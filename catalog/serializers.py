from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from catalog.models import Review
from main.models import MerchantProduct


class ProductSerializer(serializers.ModelSerializer):
    # field di bawah ini dihitung, gak disimpen langsung di tabel MerchantProduct
    merchant_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = MerchantProduct
        fields = [
            "product_id",
            "product_name",
            "merchant_name",
            "address",
            "product_stock",
            "product_status",
            "real_price",
            "discount_rate",
            "discount_price",
            "start_pickup",
            "end_pickup",
            "photo_url",
            "avg_rating",
            "review_count",
        ]

    def get_merchant_name(self, obj):
        return obj.merchant_name

    def get_address(self, obj):
        return obj.pickup_address

    def get_discount_price(self, obj):
        # discount_price itu property di model, dibuletin biar jadi angka bulat
        return int(round(obj.discount_price))

    def get_photo_url(self, obj):
        # flutter butuh alamat lengkap (http://...), bukan cuma /media/...
        url = obj.photo_url
        request = self.context.get("request")
        if url and url.startswith("/") and request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_avg_rating(self, obj):
        ratings = [review.rating for review in obj.reviews.all()]
        if not ratings:
            return 0
        return round(sum(ratings) / len(ratings), 1)

    def get_review_count(self, obj):
        return obj.reviews.count()


class ReviewSerializer(serializers.ModelSerializer):
    # 2 field ini dihitung, gak disimpen langsung di tabel Review
    username = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "username", "rating", "comment", "created_at", "is_mine"]
        read_only_fields = ["id", "created_at"]

    # proteksi XSS + minimal 5 huruf, sama kayak clean_comment di forms.py
    def validate_comment(self, value):
        value = strip_tags(value).strip()
        if len(value) < 5:
            raise serializers.ValidationError("Comment must be at least 5 characters.")
        return value

    def get_username(self, obj):
        return obj.user.username

    def get_is_mine(self, obj):
        # true kalau review ini punya user yang lagi login (buat munculin tombol edit/hapus)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return obj.user_id == request.user.id
