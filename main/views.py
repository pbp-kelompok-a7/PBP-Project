from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache

from .forms import MerchantProductForm
from .models import ConsumerProfile, MerchantProduct, OrderSystem
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from .decorators import merchant_required
from decimal import Decimal

from .forms import MerchantProductForm, ConsumerProfileForm
from .models import ConsumerProfile, MerchantProduct, OrderSystem, UserProfile
import datetime

@never_cache
def show_main(request):
    return render(request, "index.html")

### AUTHENTICATION AREA
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
        response = redirect("main:show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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

### AUTHENTICATION AREA


@login_required(login_url="main:login")
@merchant_required
@never_cache
def product_view(request):
    products = MerchantProduct.objects.filter(merchant=request.user)
    return render(request, "merchant_dashboard.html", {"products": products})


@login_required(login_url="main:login")
@merchant_required
@never_cache
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
@merchant_required
@never_cache
def product_update(request, product_id):
    product = get_object_or_404(MerchantProduct, product_id=product_id, merchant=request.user)
    form = MerchantProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produk berhasil diperbarui.")
        return redirect("main:product_view")
    return render(request, "product_form.html", {"form": form, "page_title": "Edit Produk", "product": product})


@login_required(login_url="main:login")
@merchant_required
@never_cache
def product_delete(request, product_id):
    product = get_object_or_404(MerchantProduct, product_id=product_id, merchant=request.user)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Produk berhasil dihapus.")
    return redirect("main:product_view")

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
    user_profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    if not user_profile or user_profile.role != UserProfile.Role.CONSUMER:
        messages.error(request, "Halaman ini khusus konsumen.")
        return redirect("main:show_main")

    consumer_profile = get_consumer_profile(request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "profile":
            profile_form = ConsumerProfileForm(
                request.POST,
                instance=consumer_profile,
                user=request.user,
            )
            password_form = PasswordChangeForm(request.user)

            if profile_form.is_valid():
                profile_form.save()
                messages.success(
                    request, "Profil berhasil diperbarui."
                )
                return redirect("main:edit_profile")

        elif action == "password":
            profile_form = ConsumerProfileForm(
                instance=consumer_profile,
                user=request.user,
            )
            password_form = PasswordChangeForm(
                request.user, request.POST
            )

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(
                    request, "Kata sandi berhasil diubah."
                )
                return redirect("main:edit_profile")

        else:
            return redirect("main:edit_profile")

    else:
        profile_form = ConsumerProfileForm(
            instance=consumer_profile,
            user=request.user,
        )
        password_form = PasswordChangeForm(request.user)

    return render(
        request,
        "edit_profile_view.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )

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

