from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.show_main, name="show_main"),
    path("register/", views.register, name="register"),
    path("login/", views.login_user, name="login"),
    path("profile/", views.profile, name="profile"),
    path("logout/", views.logout_user, name="logout"),
    path("merchant/products/", views.product_view, name="product_view"),
    path("merchant/products/create/", views.product_create, name="product_create"),
    path("merchant/products/<str:product_id>/edit/", views.product_update, name="product_update"),
    path("merchant/products/<str:product_id>/delete/", views.product_delete, name="product_delete"),
]
