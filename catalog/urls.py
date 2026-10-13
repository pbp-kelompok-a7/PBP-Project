from django.urls import path

from catalog.views import catalog_detail_view, catalog_list_view, get_catalog_json

app_name = "catalog"

urlpatterns = [
    path("", catalog_list_view, name="catalog_list"),
    path("json/", get_catalog_json, name="catalog_json"),
    path("<int:inventory_id>/", catalog_detail_view, name="catalog_detail"),
]