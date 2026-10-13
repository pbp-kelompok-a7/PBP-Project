from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.forms import ReviewForm
from catalog.models import Review

# data dummy dulu, nanti diganti pake MerchantInventory punya jefry
# nama field sengaja disamain sama README biar nanti gampang gantinya
DUMMY_PAKET = [
    {
        "id": 1,
        "nama_produk": "Bread Surprise Box",
        "nama_toko": "Roti Kita Bakery",
        "alamat": "Jl. Margonda Raya No. 12, Depok",
        "harga_asli": 40000,
        "harga_diskon": 15000,
        "stok_harian": 3,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Campuran roti dan pastry yang belum laku hari ini, masih fresh dan enak.",
    },
    {
        "id": 2,
        "nama_produk": "Pastry & Coffee Box",
        "nama_toko": "Kopi Senja Cafe",
        "alamat": "Jl. Kober No. 5, Depok",
        "harga_asli": 55000,
        "harga_diskon": 22000,
        "stok_harian": 5,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "22:00",
        "status": "tersedia",
        "deskripsi": "Pastry pilihan plus satu kopi susu literan buat begadang.",
    },
    {
        "id": 3,
        "nama_produk": "Cake Slice Box",
        "nama_toko": "Sweet Crumbs",
        "alamat": "Jl. Haji Asmawi No. 8, Depok",
        "harga_asli": 70000,
        "harga_diskon": 25000,
        "stok_harian": 2,
        "jam_mulai_pickup": "19:30",
        "jam_selesai_pickup": "20:30",
        "status": "tersedia",
        "deskripsi": "Beberapa potong kue dengan rasa random, bisa cheesecake, brownies, atau red velvet.",
    },
    {
        "id": 4,
        "nama_produk": "Healthy Meal Box",
        "nama_toko": "Dapur Hijau",
        "alamat": "Jl. Sawo No. 21, Depok",
        "harga_asli": 45000,
        "harga_diskon": 18000,
        "stok_harian": 4,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Menu sehat sisa hari ini, biasanya salad, nasi merah, dan lauk panggang.",
    },
    {
        "id": 5,
        "nama_produk": "Donut Mix Box",
        "nama_toko": "Bakeri Margonda",
        "alamat": "Jl. Margonda Raya No. 99, Depok",
        "harga_asli": 35000,
        "harga_diskon": 12000,
        "stok_harian": 6,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "21:30",
        "status": "tersedia",
        "deskripsi": "Isi 6 donat dengan topping campur.",
    },
    {
        "id": 6,
        "nama_produk": "Rice Box Surprise",
        "nama_toko": "Warung Rasa",
        "alamat": "Jl. Beji Timur No. 3, Depok",
        "harga_asli": 35000,
        "harga_diskon": 15000,
        "stok_harian": 3,
        "jam_mulai_pickup": "20:30",
        "jam_selesai_pickup": "21:30",
        "status": "tersedia",
        "deskripsi": "Nasi plus lauk rumahan yang tersisa hari ini.",
    },
    {
        "id": 7,
        "nama_produk": "Croissant Box",
        "nama_toko": "Croissant Corner",
        "alamat": "Jl. Juanda No. 17, Depok",
        "harga_asli": 60000,
        "harga_diskon": 20000,
        "stok_harian": 2,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "22:00",
        "status": "tersedia",
        "deskripsi": "Croissant butter, cokelat, dan almond, isinya tergantung sisa hari itu.",
    },
    {
        "id": 8,
        "nama_produk": "Toast Combo Box",
        "nama_toko": "Teh & Toast",
        "alamat": "Jl. Kukusan No. 10, Depok",
        "harga_asli": 40000,
        "harga_diskon": 16000,
        "stok_harian": 7,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Roti bakar aneka rasa plus teh manis.",
    },
    {
        # yang ini sengaja habis, buat ngetes kalau paket habis ga muncul di katalog
        "id": 9,
        "nama_produk": "Brownies Box",
        "nama_toko": "Sweet Crumbs",
        "alamat": "Jl. Haji Asmawi No. 8, Depok",
        "harga_asli": 50000,
        "harga_diskon": 20000,
        "stok_harian": 0,
        "jam_mulai_pickup": "19:30",
        "jam_selesai_pickup": "20:30",
        "status": "habis",
        "deskripsi": "Brownies panggang potong.",
    },
]


# ================= fungsi bantuan =================

def format_rupiah(angka):
    # 15000 -> Rp15.000
    return "Rp{:,}".format(angka).replace(",", ".")


def siapin_paket(paket):
    # nambahin data yang dibutuhin template: persen diskon & harga yang udah rapi
    data = dict(paket)
    data["diskon_persen"] = round((1 - paket["harga_diskon"] / paket["harga_asli"]) * 100)
    data["harga_asli_str"] = format_rupiah(paket["harga_asli"])
    data["harga_diskon_str"] = format_rupiah(paket["harga_diskon"])
    return data


def cari_paket(inventory_id):
    for paket in DUMMY_PAKET:
        if paket["id"] == inventory_id:
            return paket
    return None


def ambil_paket_tersedia():
    # cuma ambil yang statusnya tersedia & stoknya masih ada
    hasil = []
    for paket in DUMMY_PAKET:
        if paket["status"] == "tersedia" and paket["stok_harian"] > 0:
            hasil.append(siapin_paket(paket))
    # urutin dari diskon paling gede
    hasil.sort(key=lambda p: p["diskon_persen"], reverse=True)
    return hasil


def filter_paket(paket_list, keyword, harga):
    hasil = []
    for paket in paket_list:
        # filter search: cocokin ke nama produk atau nama toko
        if keyword:
            teks = (paket["nama_produk"] + " " + paket["nama_toko"]).lower()
            if keyword not in teks:
                continue

        # filter harga diskon
        h = paket["harga_diskon"]
        if harga == "lt15" and not h < 15000:
            continue
        if harga == "15to25" and not (15000 <= h <= 25000):
            continue
        if harga == "gt25" and not h > 25000:
            continue

        hasil.append(paket)
    return hasil


def ringkasan_rating(inventory_id):
    # ngitung rata-rata rating sama jumlah review satu paket
    reviews = Review.objects.filter(inventory_id=inventory_id)
    rata = reviews.aggregate(rata=Avg("rating"))["rata"]
    return {
        "rata_rata": round(rata, 1) if rata else 0,
        "jumlah": reviews.count(),
    }


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
    paket_list = ambil_paket_tersedia()
    context = {
        "paket_list": paket_list,
        "jumlah": len(paket_list),
    }
    return render(request, "catalog/catalog.html", context)


def get_catalog_json(request):
    # dipanggil lewat AJAX pas user ngetik search atau klik filter harga
    keyword = request.GET.get("q", "").strip().lower()
    harga = request.GET.get("harga", "all")
    paket_list = filter_paket(ambil_paket_tersedia(), keyword, harga)
    return JsonResponse({"jumlah": len(paket_list), "data": paket_list})


def catalog_detail_view(request, inventory_id):
    paket = cari_paket(inventory_id)
    if paket is None:
        raise Http404("Paket tidak ditemukan")

    reviews = Review.objects.filter(inventory_id=inventory_id).select_related("user")

    # cek user yang lagi login udah pernah review paket ini belum
    review_saya = None
    if request.user.is_authenticated:
        review_saya = reviews.filter(user=request.user).first()

    context = {
        "paket": siapin_paket(paket),
        "reviews": reviews,
        "rating": ringkasan_rating(inventory_id),
        "review_saya": review_saya,
    }
    return render(request, "catalog/catalog_detail.html", context)


# ================= review (CRUD) =================

def get_reviews_json(request, inventory_id):
    # READ: daftar review satu paket, dipanggil AJAX abis nambah review
    if cari_paket(inventory_id) is None:
        raise Http404("Paket tidak ditemukan")
    reviews = Review.objects.filter(inventory_id=inventory_id).select_related("user")
    data = [review_to_dict(r, request.user) for r in reviews]
    return JsonResponse({**ringkasan_rating(inventory_id), "data": data})


@login_required
@require_POST
def review_create_view(request, inventory_id):
    # CREATE: dikirim lewat AJAX dari halaman detail
    if cari_paket(inventory_id) is None:
        raise Http404("Paket tidak ditemukan")

    if Review.objects.filter(user=request.user, inventory_id=inventory_id).exists():
        return JsonResponse(
            {"success": False, "errors": {"__all__": ["You have already reviewed this box."]}},
            status=400,
        )

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.inventory_id = inventory_id
        review.save()
        return JsonResponse({"success": True, "review": review_to_dict(review, request.user)}, status=201)

    # ambil pesan errornya aja biar gampang ditampilin di JS
    errors = {
        field: [e["message"] for e in errs]
        for field, errs in form.errors.get_json_data().items()
    }
    return JsonResponse({"success": False, "errors": errors}, status=400)


@login_required
def review_update_view(request, pk):
    # UPDATE: cuma bisa edit review punya sendiri, punya orang lain jadi 404
    review = get_object_or_404(Review, pk=pk, user=request.user)
    form = ReviewForm(request.POST or None, instance=review)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("catalog:catalog_detail", inventory_id=review.inventory_id)

    context = {
        "form": form,
        "review": review,
        "paket": siapin_paket(cari_paket(review.inventory_id)),
    }
    return render(request, "catalog/review_form.html", context)


@login_required
@require_POST
def review_delete_view(request, pk):
    # DELETE: dipanggil lewat AJAX, cuma bisa hapus punya sendiri
    review = get_object_or_404(Review, pk=pk, user=request.user)
    review.delete()
    return JsonResponse({"success": True})