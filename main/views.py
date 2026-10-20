from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache

from .forms import MerchantProductForm
from .models import MerchantProduct
from .decorators import merchant_required

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
