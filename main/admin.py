from django.contrib import admin

from .models import MerchantProduct, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username",)


@admin.register(MerchantProduct)
class MerchantProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "product_name", "merchant", "product_stock", "product_status")
    list_filter = ("product_status",)
    search_fields = ("product_id", "product_name", "merchant__username")

