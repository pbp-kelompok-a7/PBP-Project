from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from catalog.models import Review
from catalog.permissions import CsrfExemptSessionAuthentication, IsLoggedInOrReadOnly
from catalog.serializers import ProductSerializer, ReviewSerializer
from catalog.views import ambil_produk_tersedia, filter_produk, order_yang_bisa_direview
from main.models import MerchantProduct


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def product_list(request):
    # cuma produk yang available & stoknya masih ada (fungsi yang sama kayak di web)
    keyword = request.query_params.get("q", "").strip()
    harga = request.query_params.get("harga", "all")
    products = filter_produk(ambil_produk_tersedia(), keyword, harga)

    serializer = ProductSerializer(products, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    product = get_object_or_404(MerchantProduct, pk=product_id)

    serializer = ProductSerializer(product, context={"request": request})
    data = serializer.data
    # info tambahan buat flutter: tombol "Tulis Review" muncul atau gak
    data["can_review"] = order_yang_bisa_direview(request.user, product) is not None
    return Response(data)


@api_view(["GET", "POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsLoggedInOrReadOnly])
def review_list(request, product_id):
    product = get_object_or_404(MerchantProduct, pk=product_id)

    if request.method == "GET":
        reviews = product.reviews.select_related("user")
        serializer = ReviewSerializer(reviews, many=True, context={"request": request})
        return Response(serializer.data)

    # sampai sini pasti POST & udah login (dicek permission di atas)
    # review cuma boleh dari order yang udah completed & belum pernah direview
    order = order_yang_bisa_direview(request.user, product)
    if order is None:
        return Response(
            {"detail": "You can only review an item after your order is completed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReviewSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    # user, product, order diisi dari server, bukan dari data yang dikirim
    serializer.save(user=request.user, product=product, order=order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def review_detail(request, review_id):
    # cuma bisa ubah/hapus review punya sendiri, punya orang lain jadi 404
    review = get_object_or_404(Review, pk=review_id, user=request.user)

    if request.method == "DELETE":
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ReviewSerializer(
        review, data=request.data, partial=True, context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
