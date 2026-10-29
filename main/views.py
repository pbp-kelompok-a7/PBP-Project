import base64
import hmac
import zlib
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import qrcode
try:
    from qrcode.image.pure import PyPNGImage
except ImportError:
    PyPNGImage = None

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.db.models import Q, ProtectedError
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from .decorators import is_merchant, merchant_required as product_merchant_required
from .forms import ConsumerProfileForm, MerchantProductForm
from .models import (
    ConsumerProfile,
    MerchantLocationIntegrator,
    MerchantProduct,
    MerchantWallet,
    OrderSystem,
    UserProfile,
    generate_payment_qr_id,
)


PAYMENT_QR_SALT = "orders.payment"
PAYMENT_QR_PREFIX = "SISABIJAK-PAY:"
PAYMENT_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PAYMENT_PNG_MARKER = b"SisaBijakPayment\x00"

@never_cache
def show_main(request):
    merchants_qs = MerchantLocationIntegrator.objects.all()
    merchants_data = [
        {
            "id_merchant": str(m.id_merchant),
            "name_merchant": m.name_merchant,
            "address": m.address,
            "latitude": float(m.latitude),
            "longitude": float(m.longitude),
        }
        for m in merchants_qs
        if m.latitude is not None and m.longitude is not None
    ]

    nearby_list = list(merchants_qs)

    if not nearby_list:
        nearby_dict = {}
        for p in MerchantProduct.objects.select_related("merchant").all():
            m_name = getattr(p, "merchant_name", None) or p.merchant.username
            addr = getattr(p, "address", "")
            key = f"{m_name}_{addr}"

            entry = nearby_dict.setdefault(
                key,
                {
                    "id_merchant": f"m-{len(nearby_dict) + 1}",
                    "name_merchant": m_name,
                    "address": addr,
                    "active_packages": 0,
                },
            )

            stock = getattr(p, "product_stock", 0) or 0
            if stock > 0:
                entry["active_packages"] += 1

        nearby_list = list(nearby_dict.values())

    deals = (
        MerchantProduct.objects
        .filter(
            product_status=MerchantProduct.Status.AVAILABLE,
            product_stock__gt=0,
            end_pickup__gt=timezone.now(),
        )
        .select_related("merchant")
        .order_by("-discount_rate", "start_pickup")[:4]
    )

    context = {
        "deals": deals,
        "deal_placeholders": range(4 - len(deals)),
        "nearby": nearby_list,
        "merchants_data": merchants_data,
    }
    return render(request, "index.html", context)


def register(request):
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect("main:login")

    return render(request, "register.html", {"form": form})


@never_cache
def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        destination = "main:product_view" if _is_merchant(user) else "main:show_main"
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
    user_profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    if user_profile and user_profile.role == UserProfile.Role.CONSUMER:
        return consumer_dashboard_view(request)

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
    return user.is_authenticated and not _is_admin(user) and is_merchant(user)


def _is_consumer(user):
    if not user.is_authenticated or _is_admin(user) or _is_merchant(user):
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role == UserProfile.Role.CONSUMER


consumer_required = user_passes_test(_is_consumer, login_url="main:login")
merchant_required = user_passes_test(_is_merchant, login_url="main:login")
merchant_or_admin_required = user_passes_test(
    lambda user: _is_merchant(user) or _is_admin(user),
    login_url="main:login",
)


def _screen(title, role):
    return {"title": title, "role": role}


def _rupiah(value):
    return f"Rp{Decimal(value):,.0f}".replace(",", ".")


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


def _payment_orders(order):
    """One row per product; a shared QR prefix groups a cart without a new model."""
    orders = OrderSystem.objects.select_for_update(of=("self",)).select_related(
        "product", "product__merchant", "consumer"
    ).filter(consumer=order.consumer)
    prefix, _, line = order.payment_qr_id.rpartition("-")
    if prefix.startswith("SBPAY-") and len(prefix) == 18 and line.isdigit():
        orders = orders.filter(payment_qr_id__startswith=prefix + "-")
    else:
        orders = orders.filter(pk=order.pk)
    orders = list(orders.order_by("pk"))
    payment_expired = any(
        item.is_payment_expired
        or item.payment_status == OrderSystem.PaymentStatus.EXPIRED
        for item in orders
    )
    for item in orders:
        if payment_expired and item.payment_status == OrderSystem.PaymentStatus.PENDING:
            item.payment_status = OrderSystem.PaymentStatus.EXPIRED
            item.save(update_fields=("payment_status",))
            _restore_stock(item)
        else:
            _expire_locked_order(item)
    return orders


def _payment_data(orders):
    return {
        "consumer": orders[0].consumer_id,
        "items": [[item.payment_qr_id, str(item.total_price)] for item in orders],
    }


def _checkout_reference(payment_qr_id):
    prefix, separator, line = payment_qr_id.rpartition("-")
    if separator and prefix.startswith("SBPAY-") and len(prefix) == 18 and line.isdigit():
        return prefix
    return payment_qr_id


def _store_claim_key(order):
    return _checkout_reference(order.payment_qr_id), order.product.merchant_id


def _store_claim_orders(order, lock=False):
    """Orders for one merchant in the checkout that issued this claim code."""
    orders = OrderSystem.objects.select_related("consumer", "product").filter(
        consumer_id=order.consumer_id,
        product__merchant_id=order.product.merchant_id,
    )
    reference = _checkout_reference(order.payment_qr_id)
    if reference != order.payment_qr_id:
        orders = orders.filter(payment_qr_id__startswith=reference + "-")
    else:
        orders = orders.filter(pk=order.pk)
    if lock:
        orders = orders.select_for_update(of=("self",))
    return list(orders.order_by("pk"))


def _claim_qr_image(code):
    image = BytesIO()
    try:
        if PyPNGImage is not None:
            qrcode.make(code, image_factory=PyPNGImage).save(image)
        else:
            raise ImportError
    except (ImportError, Exception):
        img = qrcode.make(code)
        img.save(image, format="PNG")
    return "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()


def _payment_context(orders):
    statuses = {item.payment_status for item in orders}
    if OrderSystem.PaymentStatus.EXPIRED in statuses:
        status = OrderSystem.PaymentStatus.EXPIRED
    elif statuses == {OrderSystem.PaymentStatus.COMPLETED}:
        status = OrderSystem.PaymentStatus.COMPLETED
    elif statuses <= {OrderSystem.PaymentStatus.PAID, OrderSystem.PaymentStatus.COMPLETED}:
        status = OrderSystem.PaymentStatus.PAID
    else:
        status = OrderSystem.PaymentStatus.PENDING
    return {
        "order": orders[0],
        "payment_orders": orders,
        "payment_total": sum((item.total_price for item in orders), Decimal("0")),
        "payment_deadline": min(item.payment_deadline for item in orders),
        "payment_status": status,
        "payment_status_label": status.label,
    }


def _payment_png(token):
    """Create the downloadable QR with its signed payload in a PNG text chunk."""
    image = BytesIO()
    try:
        if PyPNGImage is not None:
            qrcode.make(PAYMENT_QR_PREFIX + token, image_factory=PyPNGImage).save(image)
        else:
            raise ImportError
    except (ImportError, Exception):
        img = qrcode.make(PAYMENT_QR_PREFIX + token)
        img.save(image, format="PNG")
    png_data = image.getvalue()
    chunk_type = b"tEXt"
    chunk_data = PAYMENT_PNG_MARKER + token.encode("ascii")
    checksum = zlib.crc32(chunk_type + chunk_data).to_bytes(4, "big")
    chunk = (
        len(chunk_data).to_bytes(4, "big")
        + chunk_type
        + chunk_data
        + checksum
    )
    return png_data[:-12] + chunk + png_data[-12:]


def _read_payment_qr(upload):
    """Accept only the original PNG generated for a signed SisaBayarQR."""
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("Ukuran gambar maksimal 5 MB.")
    try:
        upload.seek(0)
        data = upload.read()
        if not data.startswith(PAYMENT_PNG_SIGNATURE):
            raise ValidationError("Unggah file PNG SisaBayarQR yang diunduh dari aplikasi.")

        token = None
        offset = len(PAYMENT_PNG_SIGNATURE)
        while offset + 12 <= len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            end = offset + 12 + length
            if end > len(data):
                break
            chunk_type = data[offset + 4:offset + 8]
            chunk_data = data[offset + 8:offset + 8 + length]
            if chunk_type == b"tEXt" and chunk_data.startswith(PAYMENT_PNG_MARKER):
                if token is not None or len(chunk_data) > 4096:
                    break
                token = chunk_data[len(PAYMENT_PNG_MARKER):].decode("ascii")
            if chunk_type == b"IEND":
                if end != len(data):
                    break
                break
            offset = end

        if not token:
            raise ValidationError("PNG bukan SisaBayarQR yang diunduh dari aplikasi.")
        signing.loads(token, salt=PAYMENT_QR_SALT)
        if not hmac.compare_digest(data, _payment_png(token)):
            raise ValidationError("Gambar QR telah diubah. Unggah PNG asli hasil unduhan.")
        return token
    except (UnicodeDecodeError, signing.BadSignature, ValueError) as error:
        raise ValidationError("Tanda tangan SisaBayarQR tidak valid.") from error
    finally:
        upload.seek(0)


@consumer_required
@never_cache
@require_http_methods(["GET", "POST"])
def checkout_view(request, product_id=None):
    cart = request.session.get("order_cart", {})
    if product_id is not None:
        product = get_object_or_404(MerchantProduct, pk=product_id)
        if (
            product.product_status != MerchantProduct.Status.AVAILABLE
            or product.product_stock < 1
            or product.end_pickup <= timezone.now() + timedelta(minutes=15)
        ):
            messages.error(request, "Produk habis atau waktu pickup sudah tidak tersedia.")
            return redirect("main:checkout")
        # The existing catalog links here; reloading must not increase quantity.
        cart.setdefault(str(product.pk), 1)
        request.session["order_cart"] = cart
        if request.method == "GET":
            return redirect("main:checkout")

    if request.method == "POST":
        remove_id = request.POST.get("remove_product")
        if remove_id:
            cart.pop(remove_id, None)
            request.session["order_cart"] = cart
            return redirect("main:checkout")
        try:
            quantities = {
                key: int(request.POST.get(
                    f"quantity_{key}",
                    request.POST.get("quantity", value) if product_id == key else value,
                ))
                for key, value in cart.items()
            }
            if not quantities or any(qty < 1 or qty > 10 for qty in quantities.values()):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Pilih produk dan isi jumlah 1 sampai 10 per produk.")
            return redirect("main:checkout")
        request.session["order_cart"] = quantities
        if request.POST.get("action") == "update":
            messages.success(request, "Keranjang diperbarui.")
            return redirect("main:checkout")

        with transaction.atomic():
            products = list(MerchantProduct.objects.select_for_update().filter(
                pk__in=quantities
            ).order_by("pk"))
            if len(products) != len(quantities) or any(
                product.product_status != MerchantProduct.Status.AVAILABLE
                or product.product_stock < quantities[product.pk]
                or product.end_pickup <= timezone.now() + timedelta(minutes=15)
                for product in products
            ):
                messages.error(request, "Stok atau jadwal pickup berubah. Periksa kembali keranjang.")
                return redirect("main:checkout")

            payment_id = generate_payment_qr_id()
            orders = []
            for index, product in enumerate(products, 1):
                quantity = quantities[product.pk]
                orders.append(OrderSystem.objects.create(
                    consumer=request.user, product=product, quantity=quantity,
                    unit_price=product.discount_price,
                    total_price=product.discount_price * quantity,
                    payment_qr_id=f"{payment_id}-{index:03d}",
                    pickup_deadline=product.end_pickup,
                ))
                product.product_stock -= quantity
                if product.product_stock == 0:
                    product.product_status = MerchantProduct.Status.SOLD_OUT
                product.save(update_fields=("product_stock", "product_status"))

        request.session["order_cart"] = {}
        return redirect("main:payment_detail", pk=orders[0].pk)

    items = []
    for product in MerchantProduct.objects.filter(pk__in=cart).select_related("merchant"):
        quantity = cart[product.pk]
        items.append({
            "product": product, "quantity": quantity,
            "total": product.discount_price * quantity,
            "original": product.real_price * quantity,
            "available": (
                product.product_status == MerchantProduct.Status.AVAILABLE
                and product.product_stock >= quantity
                and product.end_pickup > timezone.now() + timedelta(minutes=15)
            ),
        })
    request.session["order_cart"] = {item["product"].pk: item["quantity"] for item in items}
    total = sum((item["total"] for item in items), Decimal("0"))
    original = sum((item["original"] for item in items), Decimal("0"))
    return render(request, "checkout_payment.html", {
        "screen": "checkout", "screen_config": _screen("Keranjang", "consumer"),
        "cart_items": items, "cart_total": total, "cart_original": original,
        "cart_savings": original - total,
        "can_checkout": bool(items) and all(item["available"] for item in items),
    })


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
        orders = _payment_orders(_get_consumer_order(request.user, pk))
    token = signing.dumps(_payment_data(orders), salt=PAYMENT_QR_SALT, compress=True)
    context = _payment_context(orders)
    context.update({
        "screen": "payment", "screen_config": _screen("Pembayaran", "consumer"),
        "payment_qr_image": "data:image/png;base64," + base64.b64encode(_payment_png(token)).decode(),
        "status_url": reverse("main:payment_status", args=(pk,)),
        "order_list_url": f"{reverse('main:order_list')}?highlight={pk}",
    })
    return render(request, "checkout_payment.html", context)


@login_required(login_url="main:login")
@never_cache
@require_GET
def payment_status_view(request, pk):
    with transaction.atomic():
        context = _payment_context(_payment_orders(_get_consumer_order(request.user, pk)))
    return JsonResponse({
        "status": context["payment_status"],
        "status_label": context["payment_status_label"],
        "redirect_url": (
            f"{reverse('main:order_list')}?highlight={pk}"
            if context["payment_status"] in (OrderSystem.PaymentStatus.PAID, OrderSystem.PaymentStatus.COMPLETED) else None
        ),
    })


@login_required(login_url="main:login")
@never_cache
@require_http_methods(["GET", "POST"])
def simulator_bayar_view(request):
    if not _is_admin(request.user):
        raise PermissionDenied("Simulator pembayaran khusus admin.")

    context = {
        "screen": "simulator", "screen_config": _screen("Simulator Pembayaran", "admin"),
    }
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "scan":
                request.session.pop("verified_payment", None)
                upload = request.FILES.get("payment_proof")
                if upload is None:
                    raise ValidationError("Pilih gambar SisaBayarQR terlebih dahulu.")
                token = _read_payment_qr(upload)
            elif action == "confirm":
                token = request.POST.get("payment_token")
                if not token or token != request.session.get("verified_payment"):
                    raise ValidationError("Unggah dan verifikasi SisaBayarQR sebelum konfirmasi.")
            else:
                raise ValidationError("Aksi pembayaran tidak valid.")

            payload = signing.loads(token, salt=PAYMENT_QR_SALT)
            with transaction.atomic():
                first = OrderSystem.objects.filter(
                    payment_qr_id=payload["items"][0][0], consumer_id=payload["consumer"]
                ).first()
                if first is None:
                    raise ValidationError("Pesanan pada QR tidak ditemukan.")
                orders = _payment_orders(first)
                if payload != _payment_data(orders):
                    raise ValidationError("QR tidak cocok dengan rincian atau total pembayaran.")
                if any(item.payment_status != OrderSystem.PaymentStatus.PENDING for item in orders):
                    request.session.pop("verified_payment", None)
                    messages.error(request, "Pembayaran sudah diproses atau waktu pembayaran habis.")
                    return redirect("main:simulator_bayar")
                if action == "scan":
                    orders[0].payment_proof.save(upload.name, upload, save=True)
                else:
                    proof = orders[0].payment_proof
                    if not proof:
                        raise ValidationError("SisaBayarQR belum diunggah.")
                    with proof.open("rb") as saved_image:
                        if _read_payment_qr(saved_image) != token:
                            raise ValidationError("Gambar pembayaran berubah. Unggah ulang SisaBayarQR.")
                    claimed_merchants = set()
                    for item in orders:
                        merchant_id = item.product.merchant_id
                        item.mark_paid(create_claim_qr=merchant_id not in claimed_merchants)
                        claimed_merchants.add(merchant_id)

            if action == "confirm":
                request.session.pop("verified_payment", None)
                messages.success(request, "Pembayaran berhasil. QR klaim tersedia pada Pesanan Saya.")
                return redirect("main:simulator_bayar")
            request.session["verified_payment"] = token
            context.update(_payment_context(orders))
            context["payment_token"] = token
            messages.success(request, "SisaBayarQR valid. Periksa rincian sebelum konfirmasi.")
        except (ValidationError, signing.BadSignature, KeyError, IndexError, TypeError, OSError) as error:
            request.session.pop("verified_payment", None)
            message = "; ".join(error.messages) if isinstance(error, ValidationError) else "SisaBayarQR tidak valid. Silakan unggah ulang."
            messages.error(request, message)
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

    orders = list(request.user.consumer_orders.select_related("product", "product__merchant"))
    claim_codes = {}
    for item in sorted(orders, key=lambda current: current.pk):
        if item.claim_qr_code:
            claim_codes.setdefault(_store_claim_key(item), item.claim_qr_code)

    active_orders = [
        item for item in orders
        if item.payment_status in (OrderSystem.PaymentStatus.PENDING, OrderSystem.PaymentStatus.PAID)
    ]
    history_orders = [
        item for item in orders
        if item.payment_status in (OrderSystem.PaymentStatus.COMPLETED, OrderSystem.PaymentStatus.EXPIRED)
    ]
    paid_by_store = {}
    for item in active_orders:
        if item.payment_status == OrderSystem.PaymentStatus.PAID:
            paid_by_store.setdefault(_store_claim_key(item), []).append(item)
    for group_key, items in paid_by_store.items():
        code = claim_codes.get(group_key)
        for item in items:
            item.store_claim_code = code
            item.show_store_claim = item is items[0] and bool(code)
        if code:
            items[0].store_claim_items = items
            items[0].store_claim_image = _claim_qr_image(code)
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

    merchant_tab = "history" if request.GET.get("tab") == "history" else "incoming"
    status = OrderSystem.PaymentStatus.COMPLETED if merchant_tab == "history" else OrderSystem.PaymentStatus.PAID
    displayed_orders = orders.filter(payment_status=status)
    selected = None
    selected_id = request.GET.get("selected")
    if selected_id:
        selected = displayed_orders.filter(pk=selected_id).first()
    if selected is None:
        selected = displayed_orders.first()
    if selected and selected.payment_status == OrderSystem.PaymentStatus.PAID:
        code = next(
            (item.claim_qr_code for item in _store_claim_orders(selected) if item.claim_qr_code),
            None,
        )
        selected.store_claim_code = code
        if code:
            selected.store_claim_image = _claim_qr_image(code)

    wallet, _ = MerchantWallet.objects.get_or_create(merchant=request.user)
    context = {
        "screen": "merchant",
        "screen_config": _screen("Pesanan Masuk", "merchant"),
        "merchant_tab": merchant_tab,
        "displayed_orders": displayed_orders,
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
    claim_orders = []
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
            if is_ajax:
                return JsonResponse({"success": False, "error": "Kode klaim tidak ditemukan untuk merchant ini."})
            messages.error(request, "Kode klaim tidak ditemukan untuk merchant ini.")
        else:
            with transaction.atomic():
                claim_orders = _store_claim_orders(order, lock=True)
                expired = False
                for item in claim_orders:
                    expired = _expire_locked_order(item) or expired
            order = next(item for item in claim_orders if item.pk == order.pk)
            if expired:
                messages.error(request, "Sebagian produk melewati batas pengambilan.")

    if action == "confirm" and order is not None:
        with transaction.atomic():
            claim_orders = _store_claim_orders(order, lock=True)
            for item in claim_orders:
                _expire_locked_order(item)
            ready_orders = [
                item for item in claim_orders
                if item.payment_status == OrderSystem.PaymentStatus.PAID
            ]
            if not ready_orders:
                messages.error(request, "Kode ini sudah digunakan atau belum dibayar.")
                return redirect("main:validate_claim")

            total = sum((item.total_price for item in ready_orders), Decimal("0"))
            for item in ready_orders:
                item.payment_status = OrderSystem.PaymentStatus.COMPLETED
                item.save(update_fields=("payment_status",))
            wallet, _ = MerchantWallet.objects.select_for_update().get_or_create(
                merchant=request.user
            )
            wallet.balance = F("balance") + total
            wallet.save(update_fields=("balance", "updated_at"))

        messages.success(
            request,
            "QR valid. Pesanan selesai dan saldo merchant diperbarui.",
        )
        return redirect(
            f"{reverse('main:merchant_orders')}?tab=history&selected={ready_orders[0].pk}"
        )

    ready_orders = [
        item for item in claim_orders
        if item.payment_status == OrderSystem.PaymentStatus.PAID
    ]
    context = {
        "screen": "validate",
        "screen_config": _screen("Validasi QR Klaim", "merchant"),
        "order": order,
        "claim_orders": claim_orders,
        "claim_ready": bool(ready_orders),
        "claim_total": sum((item.total_price for item in ready_orders), Decimal("0")),
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
@login_required(login_url="main:login")
@never_cache
@product_merchant_required
def product_view(request):
    products = MerchantProduct.objects.filter(merchant=request.user)
    return render(request, "merchant_dashboard.html", {"products": products})


@login_required(login_url="main:login")
@never_cache
@product_merchant_required
def product_create(request):
    form = MerchantProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.merchant = request.user
        product.save()
        messages.success(request, "Produk berhasil diunggah.")
        return redirect("main:product_view")
    return render(request, "product_form.html", {"form": form, "page_title": "Tambah Produk"})


@login_required(login_url="main:login")
@never_cache
@product_merchant_required
def product_update(request, product_id):
    product = get_object_or_404(MerchantProduct, product_id=product_id, merchant=request.user)
    form = MerchantProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produk berhasil diperbarui.")
        return redirect("main:product_view")
    return render(request, "product_form.html", {"form": form, "page_title": "Edit Produk", "product": product})


@login_required(login_url="main:login")
@never_cache
@product_merchant_required
def product_delete(request, product_id):
    product = get_object_or_404(MerchantProduct, product_id=product_id, merchant=request.user)
    try:
        product.delete()
        messages.success(request, "Produk berhasil dihapus.")
    except ProtectedError:
            product.product_status = MerchantProduct.Status.INACTIVE
            product.save(update_fields=["product_status"])
            messages.info(request, "Produk sudah punya pesanan, jadi dinonaktifkan (tidak dihapus).")
    return redirect("main:product_view")


#Fitur Merchant Location Integrator

def merchant_location(request):
    query = request.GET.get('q', '').strip()
    merchants = MerchantLocationIntegrator.objects.all()

    if query:
        merchants = merchants.filter(Q(name_merchant__icontains=query) | Q(address__icontains=query))

    merchants_data = []
    for i in merchants:
        if i.latitude is not None and i.longitude is not None:
            merchants_data.append({
                "id_merchant": str(i.id_merchant),
                "name_merchant": i.name_merchant,
                "address": i.address,
                "latitude": float(i.latitude),
                "longitude": float(i.longitude),
            })
    
    context = {
        'merchants': merchants,
        'nearby': merchants,
        'merchants_data': merchants_data,
        'search_query': query,
    }
    return render(request, 'merchant_loc.html', context)
#BUILDING CONSUMER PROFILE 
def get_consumer_profile(user):
    """Mengambil atau membuat profil statistik konsumen."""
    profile, _ = ConsumerProfile.objects.get_or_create(user=user)
    return profile

#LOGIN CONSUMER PROFILE
@login_required(login_url="main:login")
@never_cache
def consumer_dashboard_view(request):
    # makesure hanya akun consumer yg bisa membuka halaman ini
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or user_profile.role != UserProfile.Role.CONSUMER:
        messages.error(request, "Halaman ini khusus konsumen.")
        return redirect("main:show_main")

    consumer_profile = get_consumer_profile(request.user)
    completed_orders = OrderSystem.objects.filter(
        consumer=request.user,
        payment_status=OrderSystem.PaymentStatus.COMPLETED,
    )

    # count penghematan dr selisih harga asli n harga diskon
    total_saved = Decimal("0.00")
    for order in completed_orders.select_related("product"):
        original_price = order.product.real_price
        discounted_price = order.unit_price
        total_saved += max(
            original_price - discounted_price, Decimal("0.00")
        ) * order.quantity

    consumer_profile.total_orders_completed = completed_orders.count()
    consumer_profile.total_money_saved = total_saved
    consumer_profile.save(update_fields=[
        "total_orders_completed",
        "total_money_saved",
    ])

    context = {
        "consumer_profile": consumer_profile,
        "total_orders_completed": consumer_profile.total_orders_completed,
        "total_money_saved": consumer_profile.total_money_saved,
        "total_co2_prevented": consumer_profile.total_co2_prevented,
    }
    return render(request, "consumer_dashboard_view.html", context)

#EDIT CONSUMER PROFILE
@login_required(login_url="main:login")
@never_cache
def edit_profile_view(request):
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or user_profile.role != UserProfile.Role.CONSUMER:
        messages.error(request, "Halaman ini khusus konsumen.")
        return redirect("main:show_main")

    consumer_profile = get_consumer_profile(request.user)

    if request.method == "POST":
        profile_form = ConsumerProfileForm(
            request.POST, instance=consumer_profile, user=request.user
        )
        password_form = PasswordChangeForm(request.user, request.POST)

        action = request.POST.get("action")
        if action == "profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("main:edit_profile")

        if action == "password" and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Kata sandi berhasil diubah.")
            return redirect("main:edit_profile")
    else:
        profile_form = ConsumerProfileForm(
            instance=consumer_profile, user=request.user
        )
        password_form = PasswordChangeForm(request.user)

    return render(request, "edit_profile_view.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })

#CONSUMER PROFILE ORDER HISTORY
@login_required(login_url="main:login")
@never_cache
def order_history_view(request):
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or user_profile.role != UserProfile.Role.CONSUMER:
        messages.error(request, "Halaman ini khusus konsumen.")
        return redirect("main:show_main")

    orders = OrderSystem.objects.filter(
        consumer=request.user
    ).select_related("product").order_by("-created_at")

    selected_status = request.GET.get("status", "")
    valid_statuses = {
        value for value, label in OrderSystem.PaymentStatus.choices
    }
    if selected_status in valid_statuses:
        orders = orders.filter(payment_status=selected_status)

    return render(request, "order_history_view.html", {
        "orders": orders,
        "selected_status": selected_status,
        "status_choices": OrderSystem.PaymentStatus.choices,
    })

