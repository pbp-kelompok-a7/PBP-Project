from django.urls import path

from catalog.views import (
    catalog_detail_view,
    catalog_list_view,
    get_catalog_json,
    get_reviews_json,
    review_create_view,
    review_delete_view,
    review_update_view,
)

app_name = "catalog"

urlpatterns = [
    path("", catalog_list_view, name="catalog_list"),
    path("json/", get_catalog_json, name="catalog_json"),
    path("<str:product_id>/", catalog_detail_view, name="catalog_detail"),
    path("<str:product_id>/reviews/json/", get_reviews_json, name="reviews_json"),
    path("<str:product_id>/reviews/create/", review_create_view, name="review_create"),
    path("reviews/<int:pk>/edit/", review_update_view, name="review_update"),
    path("reviews/<int:pk>/delete/", review_delete_view, name="review_delete"),
]