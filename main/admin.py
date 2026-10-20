from django.contrib import admin

from .models import MerchantProduct, MerchantWallet, OrderSystem, UserProfile, MerchantLocationIntegrator


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username",)


@admin.register(MerchantProduct)
class MerchantProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_id",
        "product_name",
        "merchant",
        "product_stock",
        "product_status",
        "discount_price",
    )
    list_filter = ("product_status",)
    search_fields = ("product_id", "product_name", "merchant__username")


@admin.register(OrderSystem)
class OrderSystemAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "consumer",
        "product",
        "quantity",
        "total_price",
        "payment_status",
        "created_at",
    )
    list_filter = ("payment_status", "created_at")
    search_fields = (
        "payment_qr_id",
        "claim_qr_code",
        "consumer__username",
        "product__product_name",
    )
    readonly_fields = (
        "payment_qr_id",
        "payment_proof",
        "claim_qr_code",
        "created_at",
    )


@admin.register(MerchantWallet)
class MerchantWalletAdmin(admin.ModelAdmin):
    list_display = ("merchant", "balance", "updated_at")
    search_fields = ("merchant__username",)

@admin.register(MerchantLocationIntegrator)
class MerchantLocationAdmin(admin.ModelAdmin):
    list_display = ("id_merchant", "name_merchant", "address", "latitude", "longitude")
    search_fields = ("name_merchant", "address")