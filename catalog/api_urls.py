from django.urls import path

from catalog import api_views

app_name = "catalog_api"

urlpatterns = [
    path("products/", api_views.product_list, name="product-list"),
    path("products/<str:product_id>/", api_views.product_detail, name="product-detail"),
    path("products/<str:product_id>/reviews/", api_views.review_list, name="review-list"),
    path("reviews/<int:review_id>/", api_views.review_detail, name="review-detail"),
]
