import re
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import MerchantProduct, MerchantWallet, OrderSystem


PAYMENT_QR_PATTERN = re.compile(r"SBPAY-[A-F0-9]{12}", re.IGNORECASE)


@never_cache
def show_main(request):
    return render(request, "index.html")


def register(request):
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        consumer_group, _ = Group.objects.get_or_create(name="Consumer")
        user.groups.add(consumer_group)
        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect("main:login")

    return render(request, "register.html", {"form": form})


@never_cache
def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        destination = "main:merchant_orders" if _is_merchant(user) else "main:show_main"
        response = redirect(destination)
        response.set_cookie(
            "last_login",
            timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return response

    return render(request, "login.html", {"form": form})


@login_required(login_url="main:login")
@never_cache
def profile(request):
    return render(request, "profile.html")


@never_cache
def logout_user(request):
    if request.method == "POST":
        logout(request)
        response = redirect("main:show_main")
        response.delete_cookie("last_login")
        return response

    return render(request, "logout.html")


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _is_merchant(user):
    return user.is_authenticated and user.groups.filter(
        name__in=("Merchant", "Restaurant")
    ).exists()


def _is_consumer(user):
    if not user.is_authenticated or _is_admin(user) or _is_merchant(user):
        return False
    return True


consumer_required = user_passes_test(_is_consumer, login_url="main:login")
merchant_required = user_passes_test(_is_merchant, login_url="main:login")
simulator_required = user_passes_test(
    lambda user: _is_consumer(user) or _is_admin(user),
    login_url="main:login",
)
merchant_or_admin_required = user_passes_test(
    lambda user: _is_merchant(user) or _is_admin(user),
    login_url="main:login",
)


def _screen(title, role):
    return {"title": title, "role": role}


def _rupiah(value):
    return f"Rp{Decimal(value):,.0f}".replace(",", ".")


def _tentative_pickup_window(reference_time=None):
    """Pickup tentatif dimulai 30 menit dan berakhir 90 menit setelah checkout."""

    ordered_at = reference_time or timezone.now()
    pickup_start = ordered_at + timedelta(minutes=30)
    pickup_deadline = ordered_at + timedelta(minutes=90)
    return pickup_start, pickup_deadline


def _restore_stock(order):
    MerchantProduct.objects.filter(pk=order.product_id).update(
        product_stock=F("product_stock") + order.quantity,
        product_status=MerchantProduct.Status.AVAILABLE,
    )


def _expire_locked_order(order):
    if order.is_payment_expired or order.is_pickup_expired:
        previous_status = order.payment_status
        order.payment_status = OrderSystem.PaymentStatus.EXPIRED
        order.save(update_fields=("payment_status",))
        if previous_status == OrderSystem.PaymentStatus.PENDING:
            _restore_stock(order)
        return True
    return False


def _get_consumer_order(user, pk):
    queryset = OrderSystem.objects.select_related("product", "product__merchant")
    if _is_admin(user):
        return get_object_or_404(queryset, pk=pk)
    return get_object_or_404(queryset, pk=pk, consumer=user)


@consumer_required
@never_cache
@require_http_methods(["GET", "POST"])
def checkout_view(request, product_id=None):
    products = MerchantProduct.objects.filter(
        product_status=MerchantProduct.Status.AVAILABLE,
        product_stock__gt=0,
    ).select_related("merchant")
    product = get_object_or_404(products, pk=product_id) if product_id else products.first()

    if request.method == "POST":
        if product is None:
            messages.error(request, "Belum ada produk yang tersedia untuk dipesan.")
            return redirect("main:checkout")
        try:
            quantity = int(request.POST.get("quantity", "1"))
        except ValueError:
            quantity = 0

        if quantity < 1 or quantity > 10:
            messages.error(request, "Jumlah pesanan harus antara 1 sampai 10.")
            return redirect("main:checkout_product", product_id=product.pk)

        with transaction.atomic():
            locked_product = get_object_or_404(
                MerchantProduct.objects.select_for_update(),
                pk=product.pk,
            )
            if (
                locked_product.product_status != MerchantProduct.Status.AVAILABLE
                or locked_product.product_stock < quantity
            ):
                messages.error(request, "Stok produk tidak mencukupi.")
                return redirect("main:checkout_product", product_id=product.pk)

            locked_product.product_stock -= quantity
            if locked_product.product_stock == 0:
                locked_product.product_status = MerchantProduct.Status.SOLD_OUT
            locked_product.save(update_fields=("product_stock", "product_status"))

            unit_price = locked_product.discount_price
            _, pickup_deadline = _tentative_pickup_window()
            order = OrderSystem.objects.create(
                consumer=request.user,
                product=locked_product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=unit_price * quantity,
                payment_status=OrderSystem.PaymentStatus.PENDING,
                pickup_deadline=pickup_deadline,
            )

        return redirect("main:payment_detail", pk=order.pk)

    tentative_pickup_start, tentative_pickup_deadline = _tentative_pickup_window()
    context = {
        "screen": "checkout",
        "screen_config": _screen("Checkout", "consumer"),
        "product": product,
        "products": products,
        "tentative_pickup_start": tentative_pickup_start,
        "tentative_pickup_deadline": tentative_pickup_deadline,
    }
    return render(request, "checkout_payment.html", context)


@consumer_required
@never_cache
@require_GET
def payment_view(request, pk=None):
    if pk is None:
        latest = request.user.consumer_orders.filter(
            payment_status=OrderSystem.PaymentStatus.PENDING,
        ).first()
        if latest is None:
            messages.info(request, "Belum ada pembayaran yang menunggu.")
            return redirect("main:checkout")
        return redirect("main:payment_detail", pk=latest.pk)

    with transaction.atomic():
        order = _get_consumer_order(request.user, pk)
        locked_order = OrderSystem.objects.select_for_update().get(pk=order.pk)
        _expire_locked_order(locked_order)
        order = _get_consumer_order(request.user, pk)

    context = {
        "screen": "payment",
        "screen_config": _screen("Pembayaran", "consumer"),
        "order": order,
        "status_url": reverse("main:payment_status", args=(order.pk,)),
        "order_list_url": f"{reverse('main:order_list')}?highlight={order.pk}",
    }
    return render(request, "checkout_payment.html", context)


@login_required(login_url="main:login")
@require_GET
def payment_status_view(request, pk):
    order = _get_consumer_order(request.user, pk)
    with transaction.atomic():
        locked_order = OrderSystem.objects.select_for_update().get(pk=order.pk)
        _expire_locked_order(locked_order)

    return JsonResponse(
        {
            "status": locked_order.payment_status,
            "status_label": locked_order.get_payment_status_display(),
            "redirect_url": (
                f"{reverse('main:order_list')}?highlight={locked_order.pk}"
                if locked_order.payment_status
                in (
                    OrderSystem.PaymentStatus.PAID,
                    OrderSystem.PaymentStatus.COMPLETED,
                )
                else None
            ),
        }
    )


@simulator_required
@never_cache
@require_http_methods(["GET", "POST"])
def simulator_bayar_view(request):
    order_id = request.POST.get("order_id") or request.GET.get("order")
    orders = OrderSystem.objects.select_related("product")
    if not _is_admin(request.user):
        orders = orders.filter(consumer=request.user)

    order = orders.filter(pk=order_id).first() if order_id else None
    if order is None and _is_consumer(request.user):
        order = orders.filter(
            payment_status=OrderSystem.PaymentStatus.PENDING
        ).first()

    if request.method == "POST" and request.POST.get("action") == "scan":
        upload = request.FILES.get("payment_proof")
        if upload is None:
            messages.error(request, "Pilih foto bukti pembayaran terlebih dahulu.")
        elif upload.size > 5 * 1024 * 1024 or not (
            upload.content_type or ""
        ).startswith("image/"):
            messages.error(request, "File harus berupa gambar dengan ukuran maksimal 5 MB.")
        else:
            if order is None:
                match = PAYMENT_QR_PATTERN.search(upload.name)
                if match:
                    order = orders.filter(
                        payment_qr_id__iexact=match.group(0)
                    ).first()

            if order is None:
                messages.error(
                    request,
                    "Pesanan tidak ditemukan. Buka simulator dari halaman pembayaran pesanan.",
                )
            else:
                with transaction.atomic():
                    locked_orders = OrderSystem.objects.select_for_update().select_related(
                        "product"
                    )
                    if not _is_admin(request.user):
                        locked_orders = locked_orders.filter(consumer=request.user)
                    locked_order = locked_orders.filter(pk=order.pk).first()

                    if locked_order is None:
                        messages.error(request, "Pesanan tidak dapat diakses.")
                    elif _expire_locked_order(locked_order):
                        order = locked_order
                        messages.error(request, "Waktu pembayaran sudah habis.")
                    elif locked_order.payment_status != OrderSystem.PaymentStatus.PENDING:
                        order = locked_order
                        messages.info(request, "Pembayaran pesanan ini sudah diproses.")
                    else:
                        locked_order.payment_proof = upload
                        locked_order.save(update_fields=("payment_proof",))
                        order = locked_order
                        messages.success(
                            request,
                            "Bukti pembayaran tersimpan. Periksa rincian lalu konfirmasi.",
                        )

    if request.method == "POST" and request.POST.get("action") == "confirm":
        qr_id = request.POST.get("payment_qr_id", "")
        with transaction.atomic():
            lookup = {"payment_qr_id": qr_id}
            if not _is_admin(request.user):
                lookup["consumer"] = request.user
            order = get_object_or_404(
                OrderSystem.objects.select_for_update().select_related("product"),
                **lookup,
            )
            if _expire_locked_order(order):
                messages.error(request, "Waktu pembayaran sudah habis.")
                return redirect(f"{reverse('main:simulator_bayar')}?order={order.pk}")
            if not order.payment_proof:
                messages.error(request, "Unggah bukti pembayaran sebelum konfirmasi.")
                return redirect(f"{reverse('main:simulator_bayar')}?order={order.pk}")
            try:
                order.mark_paid()
            except ValidationError as error:
                messages.error(request, "; ".join(error.messages))
                return redirect(f"{reverse('main:simulator_bayar')}?order={order.pk}")

        messages.success(request, "Pembayaran berhasil. QR klaim sudah dibuat.")
        if order.consumer_id == request.user.id:
            return redirect(f"{reverse('main:order_list')}?highlight={order.pk}")
        return redirect("main:show_main")

    context = {
        "screen": "simulator",
        "screen_config": _screen("Simulator Pembayaran", "consumer"),
        "order": order,
    }
    return render(request, "simulator_bayar.html", context)


@consumer_required
@never_cache
@require_GET
def order_list_view(request):
    orders = list(
        request.user.consumer_orders.select_related("product", "product__merchant")
    )
    for current in orders:
        if current.is_payment_expired or current.is_pickup_expired:
            with transaction.atomic():
                locked = OrderSystem.objects.select_for_update().get(pk=current.pk)
                _expire_locked_order(locked)

    orders = request.user.consumer_orders.select_related("product", "product__merchant")
    active_orders = orders.filter(
        payment_status__in=(
            OrderSystem.PaymentStatus.PENDING,
            OrderSystem.PaymentStatus.PAID,
        )
    )
    history_orders = orders.filter(
        payment_status__in=(
            OrderSystem.PaymentStatus.COMPLETED,
            OrderSystem.PaymentStatus.EXPIRED,
        )
    )
    context = {
        "screen": "orders",
        "screen_config": _screen("Pesanan Saya", "consumer"),
        "active_orders": active_orders,
        "history_orders": history_orders,
        "highlight": request.GET.get("highlight"),
    }
    return render(request, "order_list.html", context)


@merchant_required
@never_cache
@require_GET
def merchant_order_list_view(request):
    orders = OrderSystem.objects.filter(product__merchant=request.user).select_related(
        "consumer", "product"
    )
    for current in list(
        orders.filter(payment_status=OrderSystem.PaymentStatus.PAID)
    ):
        if current.is_pickup_expired:
            with transaction.atomic():
                locked = OrderSystem.objects.select_for_update().get(pk=current.pk)
                _expire_locked_order(locked)

    selected = None
    selected_id = request.GET.get("selected")
    if selected_id:
        selected = orders.filter(pk=selected_id).first()
    if selected is None:
        selected = (
            orders.filter(payment_status=OrderSystem.PaymentStatus.PAID).first()
            or orders.first()
        )

    wallet, _ = MerchantWallet.objects.get_or_create(merchant=request.user)
    context = {
        "screen": "merchant",
        "screen_config": _screen("Pesanan Masuk", "merchant"),
        "incoming_orders": orders.filter(
            payment_status=OrderSystem.PaymentStatus.PAID
        ),
        "history_orders": orders.filter(
            payment_status=OrderSystem.PaymentStatus.COMPLETED
        ),
        "selected_order": selected,
        "wallet": wallet,
    }
    return render(request, "merchant_orders.html", context)


@merchant_required
@never_cache
@require_http_methods(["GET", "POST"])
def validate_claim_view(request):
    order = None
    code = request.GET.get("code", "").strip().upper()
    action = request.POST.get("action") if request.method == "POST" else None
    if request.method == "POST":
        code = request.POST.get("claim_qr_code", "").strip().upper()

    if code:
        order = (
            OrderSystem.objects.select_related("consumer", "product")
            .filter(
                claim_qr_code=code,
                product__merchant=request.user,
            )
            .first()
        )
        if order is None:
            messages.error(request, "Kode klaim tidak ditemukan untuk merchant ini.")
        elif order.is_pickup_expired:
            with transaction.atomic():
                locked = OrderSystem.objects.select_for_update().get(pk=order.pk)
                _expire_locked_order(locked)
            order.refresh_from_db()
            messages.error(request, "Batas pengambilan pesanan sudah lewat.")

    if action == "confirm" and order is not None:
        with transaction.atomic():
            locked_order = get_object_or_404(
                OrderSystem.objects.select_for_update(),
                pk=order.pk,
                product__merchant=request.user,
            )
            if _expire_locked_order(locked_order):
                messages.error(request, "Batas pengambilan pesanan sudah lewat.")
                return redirect("main:validate_claim")
            if locked_order.payment_status != OrderSystem.PaymentStatus.PAID:
                messages.error(request, "Kode ini sudah digunakan atau belum dibayar.")
                return redirect("main:validate_claim")

            locked_order.payment_status = OrderSystem.PaymentStatus.COMPLETED
            locked_order.save(update_fields=("payment_status",))
            wallet, _ = MerchantWallet.objects.select_for_update().get_or_create(
                merchant=request.user
            )
            wallet.balance = F("balance") + locked_order.total_price
            wallet.save(update_fields=("balance", "updated_at"))

        messages.success(
            request,
            "QR valid. Pesanan selesai dan saldo merchant diperbarui.",
        )
        return redirect(
            f"{reverse('main:merchant_orders')}?selected={locked_order.pk}"
        )

    context = {
        "screen": "validate",
        "screen_config": _screen("Validasi QR Klaim", "merchant"),
        "order": order,
        "claim_code": code,
    }
    return render(request, "validate_claim.html", context)


@merchant_or_admin_required
@require_POST
def withdraw_funds_view(request):
    merchant = request.user
    if _is_admin(request.user):
        merchant_id = request.POST.get("merchant_id")
        if not merchant_id:
            raise Http404("Merchant tidak dipilih.")
        merchant = get_object_or_404(User, pk=merchant_id)

    with transaction.atomic():
        wallet, _ = MerchantWallet.objects.select_for_update().get_or_create(
            merchant=merchant
        )
        amount = wallet.balance
        if amount <= 0:
            messages.info(request, "Tidak ada saldo yang dapat dicairkan.")
        else:
            wallet.balance = Decimal("0")
            wallet.save(update_fields=("balance", "updated_at"))
            messages.success(
                request,
                f"Pencairan {_rupiah(amount)} berhasil diproses.",
            )

    if _is_merchant(request.user):
        return redirect("main:merchant_orders")
    return redirect("main:show_main")
