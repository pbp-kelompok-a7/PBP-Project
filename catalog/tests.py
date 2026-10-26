from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Review
from catalog.views import format_rupiah
from main.models import MerchantProduct, OrderSystem, UserProfile


def bikin_merchant(username, nama_toko):
    merchant = User.objects.create_user(username=username, password="pass12345", first_name=nama_toko)
    merchant.profile.role = UserProfile.Role.MERCHANT
    merchant.profile.save()
    return merchant


def bikin_produk(merchant, nama, harga, diskon, stok=5, status=MerchantProduct.ProductStatus.AVAILABLE):
    sekarang = timezone.now()
    return MerchantProduct.objects.create(
        merchant=merchant,
        product_name=nama,
        product_stock=stok,
        product_status=status,
        real_price=Decimal(harga),
        discount_rate=Decimal(diskon),
        start_pickup=sekarang + timedelta(hours=1),
        end_pickup=sekarang + timedelta(hours=2),
        address="Jl. Margonda Raya No. 12, Depok",
    )


def bikin_order(consumer, produk, status=OrderSystem.PaymentStatus.COMPLETED):
    return OrderSystem.objects.create(
        consumer=consumer,
        product=produk,
        quantity=1,
        unit_price=produk.discount_price,
        total_price=produk.discount_price,
        payment_status=status,
        pickup_deadline=timezone.now() + timedelta(hours=2),
    )


class CatalogTest(TestCase):

    def setUp(self):
        roti = bikin_merchant("roti-kita", "Roti Kita Bakery")
        kopi = bikin_merchant("kopi-senja", "Kopi Senja Cafe")
        # harga diskon: 40000 x 37.5% = 15000
        self.bread = bikin_produk(roti, "Bread Surprise Box", 40000, "62.5")
        # harga diskon: 30000 x 40% = 12000
        self.donut = bikin_produk(roti, "Donut Mix Box", 30000, "60")
        # harga diskon: 80000 x 40% = 32000
        self.cake = bikin_produk(kopi, "Cheesecake Box", 80000, "60")
        self.habis = bikin_produk(kopi, "Brownies Box", 50000, "60", stok=0)
        self.inactive = bikin_produk(
            kopi, "Soto Ayam Box", 35000, "57", status=MerchantProduct.ProductStatus.INACTIVE
        )
        self.sold_out = bikin_produk(
            kopi, "Mochi Box", 50000, "60", status=MerchantProduct.ProductStatus.SOLD_OUT
        )

    # ===== halaman katalog =====

    def test_halaman_katalog_bisa_dibuka(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/catalog.html")
        self.assertTemplateUsed(response, "base.html")

    def test_katalog_cuma_nampilin_produk_available(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertContains(response, "Bread Surprise Box")
        # stok 0, inactive, sama sold out ga boleh muncul
        self.assertNotContains(response, "Brownies Box")
        self.assertNotContains(response, "Soto Ayam Box")
        self.assertNotContains(response, "Mochi Box")
        self.assertEqual(response.context["jumlah"], 3)

    def test_katalog_nampilin_harga_dan_nama_toko(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertContains(response, "Rp15.000")
        self.assertContains(response, "Rp40.000")
        self.assertContains(response, "Roti Kita Bakery")

    def test_katalog_diurutin_dari_diskon_terbesar(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        diskon = [p["diskon_persen"] for p in response.context["produk_list"]]
        self.assertEqual(diskon, sorted(diskon, reverse=True))

    # ===== endpoint json katalog =====
    
    def test_katalog_search_dari_navbar(self):
        # search bar navbar ngirim ?q= ke halaman catalog
        response = self.client.get(reverse("catalog:catalog_list"), {"q": "donut"})
        self.assertContains(response, "Donut Mix Box")
        self.assertNotContains(response, "Cheesecake Box")
        self.assertEqual(response.context["jumlah"], 1)
        self.assertEqual(response.context["keyword"], "donut")

    def test_search_navbar_ngarah_ke_catalog(self):
        # form search di navbar harus ngirim ke /catalog/ pake name="q"
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertContains(response, f'action="{reverse("catalog:catalog_list")}"')
        self.assertContains(response, 'name="q"')
        self.assertNotContains(response, 'id="search-input"')


    def test_json_tanpa_filter(self):
        response = self.client.get(reverse("catalog:catalog_json"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jumlah"], 3)

    def test_json_search_nama_produk(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"q": "donut"})
        data = response.json()
        self.assertEqual(data["jumlah"], 1)
        self.assertEqual(data["data"][0]["product_name"], "Donut Mix Box")

    def test_json_search_nama_toko(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"q": "roti kita"})
        data = response.json()
        self.assertEqual(data["jumlah"], 2)
        for produk in data["data"]:
            self.assertEqual(produk["merchant_name"], "Roti Kita Bakery")

    def test_json_search_ga_ketemu(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"q": "ramen"})
        self.assertEqual(response.json()["jumlah"], 0)

    def test_json_filter_harga_dibawah_15rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "lt15"})
        data = response.json()
        self.assertEqual([p["product_name"] for p in data["data"]], ["Donut Mix Box"])

    def test_json_filter_harga_15rb_sampai_25rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "15to25"})
        data = response.json()
        self.assertEqual([p["product_name"] for p in data["data"]], ["Bread Surprise Box"])

    def test_json_filter_harga_diatas_25rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "gt25"})
        data = response.json()
        self.assertEqual([p["product_name"] for p in data["data"]], ["Cheesecake Box"])

    # ===== halaman detail =====

    def test_detail_bisa_dibuka(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.bread.product_id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/catalog_detail.html")
        self.assertContains(response, "Bread Surprise Box")
        self.assertContains(response, "Add to Cart")
        self.assertContains(response, "Jl. Margonda Raya No. 12, Depok")

    def test_detail_tombol_klaim_ke_checkout(self):
        user = User.objects.create_user(username="nadia", password="pass12345")
        self.client.force_login(user)
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.bread.product_id]))
        self.assertContains(response, reverse("main:checkout_product", args=[self.bread.product_id]))

    def test_detail_pickup_udah_lewat(self):
        self.bread.start_pickup = timezone.now() - timedelta(hours=2)
        self.bread.end_pickup = timezone.now() - timedelta(hours=1)
        self.bread.save()
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.bread.product_id]))
        self.assertContains(response, "Pickup Closed")
        self.assertNotContains(response, "Add to Cart")

    def test_detail_produk_stok_habis_sold_out(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.habis.product_id]))
        self.assertContains(response, "Sold Out")
        self.assertNotContains(response, "Add to Cart")

    def test_detail_produk_inactive_sold_out(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.inactive.product_id]))
        self.assertContains(response, "Sold Out")

    def test_detail_id_ga_ada_jadi_404(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=["PRD-GAADA"]))
        self.assertEqual(response.status_code, 404)

    def test_detail_guest_diminta_login(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[self.bread.product_id]))
        self.assertNotContains(response, 'id="review-form"')
        self.assertContains(response, "to write a review.")
        self.assertContains(response, reverse("main:login"))

    # ===== fungsi bantuan =====

    def test_format_rupiah(self):
        self.assertEqual(format_rupiah(15000), "Rp15.000")
        self.assertEqual(format_rupiah(Decimal("1250000.00")), "Rp1.250.000")


class ReviewTest(TestCase):

    def setUp(self):
        merchant = bikin_merchant("roti-kita", "Roti Kita Bakery")
        self.produk = bikin_produk(merchant, "Bread Surprise Box", 40000, "62.5")
        self.user = User.objects.create_user(username="nadia", password="pass12345")
        self.user_lain = User.objects.create_user(username="raka", password="pass12345")
        self.order = bikin_order(self.user, self.produk)
        self.order_lain = bikin_order(self.user_lain, self.produk)
        self.create_url = reverse("catalog:review_create", args=[self.produk.product_id])
        self.detail_url = reverse("catalog:catalog_detail", args=[self.produk.product_id])

    def login(self):
        self.client.login(username="nadia", password="pass12345")

    def bikin_review(self, user, order, rating=5, comment="enak banget"):
        return Review.objects.create(
            user=user, order=order, product=self.produk, rating=rating, comment=comment
        )

    # ===== model =====

    def test_str_review(self):
        review = self.bikin_review(self.user, self.order)
        self.assertEqual(str(review), "nadia - Bread Surprise Box (5/5)")

    # ===== create =====

    def test_create_harus_login(self):
        response = self.client.post(self.create_url, {"rating": 5, "comment": "enak banget"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)
        self.assertEqual(Review.objects.count(), 0)

    def test_create_review_berhasil(self):
        self.login()
        response = self.client.post(self.create_url, {"rating": 4, "comment": "porsinya pas"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        review = Review.objects.get()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.order, self.order)
        self.assertEqual(review.product, self.produk)

    def test_create_tanpa_order_completed_ditolak(self):
        # order masih paid (belum diambil), jadi belum boleh review
        self.order.payment_status = OrderSystem.PaymentStatus.PAID
        self.order.save()
        self.login()
        response = self.client.post(self.create_url, {"rating": 5, "comment": "enak banget"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def test_satu_order_cuma_bisa_sekali_review(self):
        self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.post(self.create_url, {"rating": 3, "comment": "review kedua"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.filter(user=self.user).count(), 1)

    def test_order_kedua_bisa_review_lagi(self):
        self.bikin_review(self.user, self.order)
        bikin_order(self.user, self.produk)
        self.login()
        response = self.client.post(self.create_url, {"rating": 3, "comment": "beli lagi tetep enak"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Review.objects.filter(user=self.user).count(), 2)

    def test_create_rating_ga_valid(self):
        self.login()
        response = self.client.post(self.create_url, {"rating": 9, "comment": "porsinya pas"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.json()["errors"])

    def test_create_komentar_kependekan(self):
        self.login()
        response = self.client.post(self.create_url, {"rating": 5, "comment": "ok"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("comment", response.json()["errors"])

    def test_create_produk_ga_ada(self):
        self.login()
        url = reverse("catalog:review_create", args=["PRD-GAADA"])
        response = self.client.post(url, {"rating": 5, "comment": "enak banget"})
        self.assertEqual(response.status_code, 404)

    def test_create_pake_get_ditolak(self):
        self.login()
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 405)

    # ===== read =====

    def test_reviews_json(self):
        self.bikin_review(self.user, self.order, rating=5)
        self.bikin_review(self.user_lain, self.order_lain, rating=4)
        self.login()
        response = self.client.get(reverse("catalog:reviews_json", args=[self.produk.product_id]))
        data = response.json()
        self.assertEqual(data["jumlah"], 2)
        self.assertEqual(data["rata_rata"], 4.5)
        # cuma 1 yang punya nadia
        punya_sendiri = [r for r in data["data"] if r["punya_sendiri"]]
        self.assertEqual(len(punya_sendiri), 1)

    def test_reviews_json_produk_ga_ada(self):
        response = self.client.get(reverse("catalog:reviews_json", args=["PRD-GAADA"]))
        self.assertEqual(response.status_code, 404)

    def test_detail_nampilin_review(self):
        self.bikin_review(self.user_lain, self.order_lain, comment="roti kejunya mantap")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "roti kejunya mantap")
        self.assertContains(response, "raka")

    def test_detail_punya_order_completed_ada_form(self):
        self.login()
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'id="review-form"')

    def test_detail_belum_pernah_order_ga_ada_form(self):
        User.objects.create_user(username="baru", password="pass12345")
        self.client.login(username="baru", password="pass12345")
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, 'id="review-form"')
        self.assertContains(response, "after you pick up this box")

    def test_detail_udah_review_form_ilang(self):
        self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, 'id="review-form"')
        self.assertContains(response, "already reviewed this box")

    # ===== update =====

    def test_halaman_edit_bisa_dibuka(self):
        review = self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.get(reverse("catalog:review_update", args=[review.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/review_form.html")

    def test_edit_review_berhasil(self):
        review = self.bikin_review(self.user, self.order, rating=5)
        self.login()
        response = self.client.post(
            reverse("catalog:review_update", args=[review.id]),
            {"rating": 2, "comment": "ternyata agak keras rotinya"},
        )
        self.assertRedirects(response, self.detail_url)
        review.refresh_from_db()
        self.assertEqual(review.rating, 2)

    def test_edit_data_ga_valid(self):
        review = self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.post(
            reverse("catalog:review_update", args=[review.id]),
            {"rating": 9, "comment": "ok"},
        )
        # balik ke form lagi, ga ke-redirect
        self.assertEqual(response.status_code, 200)

    def test_ga_bisa_edit_punya_orang(self):
        review = self.bikin_review(self.user_lain, self.order_lain)
        self.login()
        response = self.client.get(reverse("catalog:review_update", args=[review.id]))
        self.assertEqual(response.status_code, 404)

    # ===== delete =====

    def test_hapus_review_berhasil(self):
        review = self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.post(reverse("catalog:review_delete", args=[review.id]))
        self.assertTrue(response.json()["success"])
        self.assertEqual(Review.objects.count(), 0)

    def test_ga_bisa_hapus_punya_orang(self):
        review = self.bikin_review(self.user_lain, self.order_lain)
        self.login()
        response = self.client.post(reverse("catalog:review_delete", args=[review.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 1)

    def test_hapus_pake_get_ditolak(self):
        review = self.bikin_review(self.user, self.order)
        self.login()
        response = self.client.get(reverse("catalog:review_delete", args=[review.id]))
        self.assertEqual(response.status_code, 405)


class SeedCatalogTest(TestCase):

    def test_seed_bikin_50_produk(self):
        call_command("seed_catalog", stdout=StringIO())
        self.assertEqual(MerchantProduct.objects.count(), 50)
        produk = MerchantProduct.objects.get(product_name="Bread Surprise Box")
        self.assertEqual(produk.discount_price, Decimal("15000.00"))
        self.assertEqual(produk.merchant_name, "Roti Kita Bakery")
        self.assertEqual(produk.merchant.profile.role, UserProfile.Role.MERCHANT)
        # 60000 diskon ke 20000 itu 66.67%, dibuletin jadi 67% biar harganya Rp19.800
        croissant = MerchantProduct.objects.get(product_name="Croissant Box")
        self.assertEqual(croissant.discount_rate, Decimal("67.00"))
        self.assertEqual(croissant.discount_price, Decimal("19800.00"))

    def test_seed_jam_pickup_masih_bisa_dicheckout(self):
        call_command("seed_catalog", stdout=StringIO())
        batas = timezone.now() + timedelta(minutes=15)
        self.assertFalse(MerchantProduct.objects.filter(end_pickup__lte=batas).exists())

    def test_seed_dua_kali_ga_dobel(self):
        call_command("seed_catalog", stdout=StringIO())
        call_command("seed_catalog", stdout=StringIO())
        self.assertEqual(MerchantProduct.objects.count(), 50)

    def test_seed_demo_consumer(self):
        User.objects.create_user(username="nadia", password="pass12345")
        call_command("seed_catalog", demo_consumer="nadia", stdout=StringIO())
        call_command("seed_catalog", demo_consumer="nadia", stdout=StringIO())
        orders = OrderSystem.objects.filter(consumer__username="nadia")
        self.assertEqual(orders.count(), 3)
        self.assertTrue(all(o.payment_status == OrderSystem.PaymentStatus.COMPLETED for o in orders))

    def test_seed_demo_consumer_ga_ada(self):
        with self.assertRaises(CommandError):
            call_command("seed_catalog", demo_consumer="hantu", stdout=StringIO())