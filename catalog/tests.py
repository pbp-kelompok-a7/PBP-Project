from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalog.models import Review
from catalog.views import format_rupiah


class CatalogTest(TestCase):

    # ===== halaman katalog =====

    def test_halaman_katalog_bisa_dibuka(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/catalog.html")

    def test_katalog_cuma_nampilin_paket_tersedia(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        # brownies box stoknya 0 jadi ga boleh muncul
        self.assertNotContains(response, "Brownies Box")
        self.assertContains(response, "Bread Surprise Box")

    def test_katalog_diurutin_dari_diskon_terbesar(self):
        response = self.client.get(reverse("catalog:catalog_list"))
        diskon = [p["diskon_persen"] for p in response.context["paket_list"]]
        self.assertEqual(diskon, sorted(diskon, reverse=True))

    # ===== endpoint json katalog =====

    def test_json_tanpa_filter(self):
        response = self.client.get(reverse("catalog:catalog_json"))
        self.assertEqual(response.status_code, 200)
        # ada 8 paket tersedia di data dummy
        self.assertEqual(response.json()["jumlah"], 8)

    def test_json_search_nama_toko(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"q": "roti"})
        data = response.json()
        self.assertEqual(data["jumlah"], 1)
        self.assertEqual(data["data"][0]["nama_toko"], "Roti Kita Bakery")

    def test_json_search_ga_ketemu(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"q": "pizza"})
        self.assertEqual(response.json()["jumlah"], 0)

    def test_json_filter_harga_dibawah_15rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "lt15"})
        for paket in response.json()["data"]:
            self.assertLess(paket["harga_diskon"], 15000)

    def test_json_filter_harga_15rb_sampai_25rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "15to25"})
        for paket in response.json()["data"]:
            self.assertTrue(15000 <= paket["harga_diskon"] <= 25000)

    def test_json_filter_harga_diatas_25rb(self):
        response = self.client.get(reverse("catalog:catalog_json"), {"harga": "gt25"})
        # di data dummy ga ada yang diatas 25rb
        self.assertEqual(response.json()["jumlah"], 0)

    # ===== halaman detail =====

    def test_detail_bisa_dibuka(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/catalog_detail.html")
        self.assertContains(response, "Bread Surprise Box")
        self.assertContains(response, "Claim Mystery Box")

    def test_detail_paket_habis_muncul_sold_out(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[9]))
        self.assertContains(response, "Sold Out")
        self.assertNotContains(response, "Claim Mystery Box")

    def test_detail_id_ga_ada_jadi_404(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_detail_guest_ga_ada_form_review(self):
        response = self.client.get(reverse("catalog:catalog_detail", args=[1]))
        self.assertNotContains(response, 'id="review-form"')
        self.assertContains(response, "Log in as Consumer to write a review.")

    # ===== fungsi bantuan =====

    def test_format_rupiah(self):
        self.assertEqual(format_rupiah(15000), "Rp15.000")
        self.assertEqual(format_rupiah(1250000), "Rp1.250.000")


class ReviewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="nadia", password="pass12345")
        self.user_lain = User.objects.create_user(username="raka", password="pass12345")
        self.create_url = reverse("catalog:review_create", args=[1])

    def login(self):
        self.client.login(username="nadia", password="pass12345")

    def bikin_review(self, user, rating=5, comment="enak banget"):
        return Review.objects.create(user=user, inventory_id=1, rating=rating, comment=comment)

    # ===== model =====

    def test_str_review(self):
        review = self.bikin_review(self.user)
        self.assertEqual(str(review), "nadia - paket 1 (5/5)")

    # ===== create =====

    def test_create_harus_login(self):
        response = self.client.post(self.create_url, {"rating": 5, "comment": "enak banget"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_create_review_berhasil(self):
        self.login()
        response = self.client.post(self.create_url, {"rating": 4, "comment": "porsinya pas"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().user, self.user)

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

    def test_create_dua_kali_ditolak(self):
        self.login()
        self.bikin_review(self.user)
        response = self.client.post(self.create_url, {"rating": 3, "comment": "review kedua"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 1)

    def test_create_paket_ga_ada(self):
        self.login()
        url = reverse("catalog:review_create", args=[999])
        response = self.client.post(url, {"rating": 5, "comment": "enak banget"})
        self.assertEqual(response.status_code, 404)

    def test_create_pake_get_ditolak(self):
        self.login()
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 405)

    # ===== read =====

    def test_reviews_json(self):
        self.bikin_review(self.user, rating=5)
        self.bikin_review(self.user_lain, rating=4)
        self.login()
        response = self.client.get(reverse("catalog:reviews_json", args=[1]))
        data = response.json()
        self.assertEqual(data["jumlah"], 2)
        self.assertEqual(data["rata_rata"], 4.5)
        # cuma 1 yang punya nadia
        punya_sendiri = [r for r in data["data"] if r["punya_sendiri"]]
        self.assertEqual(len(punya_sendiri), 1)

    def test_reviews_json_paket_ga_ada(self):
        response = self.client.get(reverse("catalog:reviews_json", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_detail_nampilin_review(self):
        self.bikin_review(self.user_lain, comment="roti kejunya mantap")
        response = self.client.get(reverse("catalog:catalog_detail", args=[1]))
        self.assertContains(response, "roti kejunya mantap")
        self.assertContains(response, "raka")

    def test_detail_login_belum_review_ada_form(self):
        self.login()
        response = self.client.get(reverse("catalog:catalog_detail", args=[1]))
        self.assertContains(response, 'id="review-form"')

    def test_detail_udah_review_form_ilang(self):
        self.bikin_review(self.user)
        self.login()
        response = self.client.get(reverse("catalog:catalog_detail", args=[1]))
        self.assertNotContains(response, 'id="review-form"')
        self.assertContains(response, "already reviewed this box")

    # ===== update =====

    def test_halaman_edit_bisa_dibuka(self):
        review = self.bikin_review(self.user)
        self.login()
        response = self.client.get(reverse("catalog:review_update", args=[review.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/review_form.html")

    def test_edit_review_berhasil(self):
        review = self.bikin_review(self.user, rating=5)
        self.login()
        response = self.client.post(
            reverse("catalog:review_update", args=[review.id]),
            {"rating": 2, "comment": "ternyata agak keras rotinya"},
        )
        self.assertRedirects(response, reverse("catalog:catalog_detail", args=[1]))
        review.refresh_from_db()
        self.assertEqual(review.rating, 2)

    def test_edit_data_ga_valid(self):
        review = self.bikin_review(self.user)
        self.login()
        response = self.client.post(
            reverse("catalog:review_update", args=[review.id]),
            {"rating": 9, "comment": "ok"},
        )
        # balik ke form lagi, ga ke-redirect
        self.assertEqual(response.status_code, 200)

    def test_ga_bisa_edit_punya_orang(self):
        review = self.bikin_review(self.user_lain)
        self.login()
        response = self.client.get(reverse("catalog:review_update", args=[review.id]))
        self.assertEqual(response.status_code, 404)

    # ===== delete =====

    def test_hapus_review_berhasil(self):
        review = self.bikin_review(self.user)
        self.login()
        response = self.client.post(reverse("catalog:review_delete", args=[review.id]))
        self.assertTrue(response.json()["success"])
        self.assertEqual(Review.objects.count(), 0)

    def test_ga_bisa_hapus_punya_orang(self):
        review = self.bikin_review(self.user_lain)
        self.login()
        response = self.client.post(reverse("catalog:review_delete", args=[review.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 1)

    def test_hapus_pake_get_ditolak(self):
        review = self.bikin_review(self.user)
        self.login()
        response = self.client.get(reverse("catalog:review_delete", args=[review.id]))
        self.assertEqual(response.status_code, 405)