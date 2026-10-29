
from django.urls import path

from . import views


app_name = "main"

urlpatterns = [
    # Main pages and authentication
    path("", views.show_main, name="show_main"),
    path("register/", views.register, name="register"),
    path("login/", views.login_user, name="login"),
    path("profile/", views.profile, name="profile"),
    path("logout/", views.logout_user, name="logout"),

    #ConsumerProfile
    path( #untuk mengedit profil dan mengubah password konsumen
        "consumer/edit-profile/",
        views.edit_profile_view,
        name="edit_profile",
    ),
    path( #untuk melihat riwayat pesanan konsumen
        "consumer/orders/",
        views.order_history_view,
        name="order_history",
    ),

    # Order system
    path("orders/", views.checkout_view, name="order_index"),
    path("orders/checkout/", views.checkout_view, name="checkout"),
    path(
        "orders/checkout/<str:product_id>/",
        views.checkout_view,
        name="checkout_product",
    ),
    path("orders/payment/", views.payment_view, name="payment"),
    path(
        "orders/payment/<int:pk>/",
        views.payment_view,
        name="payment_detail",
    ),
    path(
        "orders/payment/<int:pk>/status/",
        views.payment_status_view,
        name="payment_status",
    ),
    path(
        "orders/simulator-bayar/",
        views.simulator_bayar_view,
        name="simulator_bayar",
    ),
    path(
        "orders/my-orders/",
        views.order_list_view,
        name="order_list",
    ),
    path(
        "orders/merchant/",
        views.merchant_order_list_view,
        name="merchant_orders",
    ),
    path(
        "orders/merchant/validate/",
        views.validate_claim_view,
        name="validate_claim",
    ),
    path(
        "orders/merchant/withdraw/",
        views.withdraw_funds_view,
        name="withdraw_funds",
    ),

    # Merchant products
    path(
        "merchant/products/",
        views.product_view,
        name="product_view",
    ),
    path(
        "merchant/products/create/",
        views.product_create,
        name="product_create",
    ),
    path(
        "merchant/products/<str:product_id>/edit/",
        views.product_update,
        name="product_update",
    ),
    path(
        "merchant/products/<str:product_id>/delete/",
        views.product_delete,
        name="product_delete",
    ),

    # Merchant location integrator (PR #24)
    path(
        "maps/",
        views.merchant_location,
        name="merchant_location",
    ),
]
