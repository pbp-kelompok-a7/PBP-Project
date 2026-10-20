from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import UserProfile


def is_merchant(user):
    """Admin tidak dianggap Merchant; akses admin tetap melalui Django Admin."""
    if not user.is_authenticated or user.is_superuser:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role == UserProfile.Role.MERCHANT

# Decorator untuk verifikasi suatu method yang bisa dijalankan oleh role Merchant
def merchant_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_merchant(request.user):
            messages.error(request, "Halaman ini hanya dapat diakses oleh akun Merchant.")
            return redirect("main:show_main")
        return view_func(request, *args, **kwargs)

    return wrapped_view
