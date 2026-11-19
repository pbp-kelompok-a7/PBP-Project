from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from catalog.models import Review
from main.models import MerchantProduct, OrderSystem, UserProfile


def bikin_produk(merchant, nama, harga, diskon, stok=5):
    sekarang = timezone.now()
    return MerchantProduct.objects.create(
        merchant=merchant,
        product_name=nama,
        product_stock=stok,
        real_price=Decimal(harga),
        discount_rate=Decimal(diskon),
        start_pickup=sekarang + timedelta(hours=1),
        end_pickup=sekarang + timedelta(hours=2),
        address="Jl. Margonda Raya No. 12, Depok",
    )


class CatalogAPITest(APITestCase):
    def setUp(self):
        self.merchant = User.objects.create_user(
            username="roti-kita", password="test-password", first_name="Roti Kita Bakery",
        )
        self.merchant.profile.role = UserProfile.Role.MERCHANT
        self.merchant.profile.save()
        self.consumer = User.objects.create_user(username="nadia", password="test-password")
        self.visitor = User.objects.create_user(username="budi", password="test-password")

        # harga diskon: 40000 x 37.5% = 15000
        self.bread = bikin_produk(self.merchant, "Bread Surprise", 40000, "62.5")
        # harga diskon: 30000 x 40% = 12000
        self.donut = bikin_produk(self.merchant, "Donut Mix", 30000, "60")
        # stok 0 jadi gak boleh muncul di katalog
        self.habis = bikin_produk(self.merchant, "Brownies", 50000, "60", stok=0)

        # nadia udah pernah beli bread (completed), jadi boleh review bread
        self.order = OrderSystem.objects.create(
            consumer=self.consumer,
            product=self.bread,
            quantity=1,
            unit_price=self.bread.discount_price,
            total_price=self.bread.discount_price,
            payment_status=OrderSystem.PaymentStatus.COMPLETED,
            pickup_deadline=timezone.now() + timedelta(hours=2),
        )

        self.list_url = reverse("catalog_api:product-list")
        self.detail_url = reverse("catalog_api:product-detail", args=[self.bread.product_id])
        self.review_url = reverse("catalog_api:review-list", args=[self.bread.product_id])
        self.payload = {"rating": 5, "comment": "Rotinya masih empuk banget"}

    # ===== produk =====

    def test_list_produk_cuma_yang_available(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nama = [p["product_name"] for p in response.data]
        self.assertIn("Bread Surprise", nama)
        self.assertNotIn("Brownies", nama)

    def test_list_produk_search(self):
        response = self.client.get(self.list_url, {"q": "donut"})
        self.assertEqual([p["product_name"] for p in response.data], ["Donut Mix"])

    def test_list_produk_filter_harga(self):
        response = self.client.get(self.list_url, {"harga": "15to25"})
        self.assertEqual([p["product_name"] for p in response.data], ["Bread Surprise"])

    def test_detail_produk(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["product_name"], "Bread Surprise")
        self.assertEqual(response.data["discount_price"], 15000)
        self.assertEqual(response.data["merchant_name"], "Roti Kita Bakery")
        self.assertFalse(response.data["can_review"])

    def test_detail_produk_can_review_kalau_udah_beli(self):
        self.client.force_login(self.consumer)
        response = self.client.get(self.detail_url)
        self.assertTrue(response.data["can_review"])

    def test_detail_produk_gak_ada(self):
        response = self.client.get(reverse("catalog_api:product-detail", args=["gak-ada"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ===== review =====

    def test_list_review_bisa_dibuka_tanpa_login(self):
        Review.objects.create(
            user=self.consumer, product=self.bread, order=self.order, rating=4, comment="Enak banget",
        )
        response = self.client.get(self.review_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertFalse(response.data[0]["is_mine"])

    def test_bikin_review_harus_login(self):
        response = self.client.post(self.review_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 0)

    def test_bikin_review_berhasil(self):
        self.client.force_login(self.consumer)
        response = self.client.post(self.review_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        self.assertTrue(response.data["is_mine"])
        # rating rata-rata produk ikut berubah
        detail = self.client.get(self.detail_url)
        self.assertEqual(detail.data["avg_rating"], 5)
        self.assertEqual(detail.data["review_count"], 1)

    def test_bikin_review_tanpa_order_ditolak(self):
        self.client.force_login(self.visitor)
        response = self.client.post(self.review_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.count(), 0)

    def test_bikin_review_komentar_kependekan(self):
        self.client.force_login(self.consumer)
        response = self.client.post(self.review_url, {"rating": 5, "comment": "ok"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", response.data)

    def test_bikin_review_tanpa_csrf_token_tetap_bisa(self):
        # flutter gak ngirim csrf token, jadi api-nya harus tetap jalan
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.consumer)
        response = client.post(self.review_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edit_dan_hapus_review_sendiri(self):
        review = Review.objects.create(
            user=self.consumer, product=self.bread, order=self.order, rating=3, comment="Lumayan enak",
        )
        url = reverse("catalog_api:review-detail", args=[review.id])
        self.client.force_login(self.consumer)

        response = self.client.patch(url, {"rating": 4})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=review.id).exists())

    def test_gak_bisa_ubah_review_orang_lain(self):
        review = Review.objects.create(
            user=self.consumer, product=self.bread, order=self.order, rating=3, comment="Lumayan enak",
        )
        url = reverse("catalog_api:review-detail", args=[review.id])
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.patch(url, {"rating": 1}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
