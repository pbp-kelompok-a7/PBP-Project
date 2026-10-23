from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.forms import ReviewForm
from catalog.models import Review
from main.models import MerchantProduct, OrderSystem

LOGIN_URL = "main:login"


# ================= fungsi bantuan =================

def format_rupiah(angka):
    # 15000 -> Rp15.000 (harga dari model bentuknya Decimal, jadi dibuletin dulu)
    return "Rp{:,}".format(int(round(angka))).replace(",", ".")


def jam(waktu):
    # ambil jam:menit aja dari DateTimeField, pake zona waktu Jakarta
    return timezone.localtime(waktu).strftime("%H:%M")


def produk_to_dict(produk):
    # ubah MerchantProduct jadi dict biar bisa dipake di template sama json
    real_price = int(round(produk.real_price))
    discount_price = int(round(produk.discount_price))
    return {
        "product_id": produk.product_id,
        "product_name": produk.product_name,
        "merchant_name": produk.merchant_name,
        "address": produk.pickup_address,
        "product_stock": produk.product_stock,
        "start_pickup": jam(produk.start_pickup),
        "end_pickup": jam(produk.end_pickup),
        "real_price": real_price,
        "discount_price": discount_price,
        "diskon_persen": int(round(produk.discount_rate)),
        "real_price_str": format_rupiah(real_price),
        "discount_price_str": format_rupiah(discount_price),
    }


def masih_tersedia(produk):
    return (
        produk.product_status == MerchantProduct.ProductStatus.AVAILABLE
        and produk.product_stock > 0
    )

def masih_bisa_diklaim(produk):
    # disamain sama aturan checkout darius: jam pickup-nya minimal masih 15 menit lagi
    return masih_tersedia(produk) and produk.end_pickup > timezone.now() + timedelta(minutes=15)

def ambil_produk_tersedia():
    # cuma ambil yang statusnya Available & stoknya masih ada, urut dari diskon paling gede
    return (
        MerchantProduct.objects.filter(
            product_status=MerchantProduct.ProductStatus.AVAILABLE,
            product_stock__gt=0,
        )
        .select_related("merchant")
        .order_by("-discount_rate", "product_name")
    )


def filter_produk(queryset, keyword, harga):
    # filter search: cocokin ke nama produk atau nama toko
    if keyword:
        queryset = queryset.filter(
            Q(product_name__icontains=keyword)
            | Q(merchant__first_name__icontains=keyword)
            | Q(merchant__username__icontains=keyword)
        )

    # discount_price itu property (dihitung dari real_price & discount_rate),
    # jadi filter harganya dicek satu-satu di python
    hasil = []
    for produk in queryset:
        h = produk.discount_price
        if harga == "lt15" and not h < 15000:
            continue
        if harga == "15to25" and not (15000 <= h <= 25000):
            continue
        if harga == "gt25" and not h > 25000:
            continue
        hasil.append(produk)
    return hasil


def ringkasan_rating(produk):
    # ngitung rata-rata rating sama jumlah review satu produk
    reviews = produk.reviews.all()
    rata = reviews.aggregate(rata=Avg("rating"))["rata"]
    return {
        "rata_rata": round(rata, 1) if rata else 0,
        "jumlah": reviews.count(),
    }


def order_yang_bisa_direview(user, produk):
    # order punya user ini buat produk ini yang udah completed tapi belum direview
    if not user.is_authenticated:
        return None
    return (
        OrderSystem.objects.filter(
            consumer=user,
            product=produk,
            payment_status=OrderSystem.PaymentStatus.COMPLETED,
            review__isnull=True,
        )
        .order_by("created_at")
        .first()
    )


def review_to_dict(review, user):
    # ubah review jadi dict biar bisa dikirim lewat json
    return {
        "id": review.id,
        "username": review.user.username,
        "rating": review.rating,
        "comment": review.comment,
        "tanggal": timezone.localtime(review.created_at).strftime("%d %b %Y"),
        "punya_sendiri": bool(user.is_authenticated and review.user_id == user.id),
        "edit_url": reverse("catalog:review_update", args=[review.id]),
        "delete_url": reverse("catalog:review_delete", args=[review.id]),
    }


# ================= katalog =================

def catalog_list_view(request):
    # keyword dari search bar navbar (kalau user nyari dari halaman lain)
    keyword = request.GET.get("q", "").strip()
    hasil = filter_produk(ambil_produk_tersedia(), keyword, "all")
    produk_list = [produk_to_dict(p) for p in hasil]
    context = {
        "produk_list": produk_list,
        "jumlah": len(produk_list),
        "keyword": keyword,
    }
    return render(request, "catalog/catalog.html", context)


def get_catalog_json(request):
    # dipanggil lewat AJAX pas user ngetik search atau klik filter harga
    keyword = request.GET.get("q", "").strip()
    harga = request.GET.get("harga", "all")
    hasil = filter_produk(ambil_produk_tersedia(), keyword, harga)
    data = [produk_to_dict(p) for p in hasil]
    return JsonResponse({"jumlah": len(data), "data": data})


def catalog_detail_view(request, product_id):
    produk = get_object_or_404(MerchantProduct.objects.select_related("merchant"), pk=product_id)
    reviews = produk.reviews.select_related("user")

    sudah_review = request.user.is_authenticated and reviews.filter(user=request.user).exists()

    context = {
        "produk": produk_to_dict(produk),
        "tersedia": masih_tersedia(produk),
        "bisa_klaim": masih_bisa_diklaim(produk),
        "reviews": reviews,
        "rating": ringkasan_rating(produk),
        "order_review": order_yang_bisa_direview(request.user, produk),
        "sudah_review": sudah_review,
    }
    return render(request, "catalog/catalog_detail.html", context)


# ================= review (CRUD) =================

def get_reviews_json(request, product_id):
    # READ: daftar review + rata-rata rating satu produk
    produk = get_object_or_404(MerchantProduct, pk=product_id)
    reviews = produk.reviews.select_related("user")
    data = [review_to_dict(r, request.user) for r in reviews]
    return JsonResponse({**ringkasan_rating(produk), "data": data})


@login_required(login_url=LOGIN_URL)
@require_POST
def review_create_view(request, product_id):
    # CREATE: dikirim lewat AJAX dari halaman detail
    produk = get_object_or_404(MerchantProduct, pk=product_id)

    # review cuma boleh dari order yang udah completed & belum pernah direview
    order = order_yang_bisa_direview(request.user, produk)
    if order is None:
        return JsonResponse(
            {"success": False, "errors": {"__all__": ["You can only review a box after your order is completed."]}},
            status=400,
        )

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = produk
        review.order = order
        review.save()
        return JsonResponse({"success": True, "review": review_to_dict(review, request.user)}, status=201)

    # ambil pesan errornya aja biar gampang ditampilin di JS
    errors = {
        field: [e["message"] for e in errs]
        for field, errs in form.errors.get_json_data().items()
    }
    return JsonResponse({"success": False, "errors": errors}, status=400)


@login_required(login_url=LOGIN_URL)
def review_update_view(request, pk):
    # UPDATE: cuma bisa edit review punya sendiri, punya orang lain jadi 404
    review = get_object_or_404(Review.objects.select_related("product__merchant"), pk=pk, user=request.user)
    form = ReviewForm(request.POST or None, instance=review)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("catalog:catalog_detail", product_id=review.product_id)

    context = {
        "form": form,
        "review": review,
        "produk": produk_to_dict(review.product),
    }
    return render(request, "catalog/review_form.html", context)


@login_required(login_url=LOGIN_URL)
@require_POST
def review_delete_view(request, pk):
    # DELETE: dipanggil lewat AJAX, cuma bisa hapus punya sendiri
    review = get_object_or_404(Review, pk=pk, user=request.user)
    review.delete()
    return JsonResponse({"success": True})