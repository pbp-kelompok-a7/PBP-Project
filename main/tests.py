import base64
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

import qrcode
from PIL import Image

from django.contrib.auth.models import User
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import MerchantProduct, MerchantWallet, OrderSystem, UserProfile


class OrderSystemFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="payment-admin", password="test-password", email="admin@example.test",
        )
        cls.consumer = User.objects.create_user(
            username="ayu",
            password="test-password",
        )
        cls.other_consumer = User.objects.create_user(
            username="budi",
            password="test-password",
        )

        cls.merchant = User.objects.create_user(
            username="roti-kita",
            password="test-password",
        )
        cls.merchant.profile.role = UserProfile.Role.MERCHANT
        cls.merchant.profile.save(update_fields=("role",))
        cls.other_merchant = User.objects.create_user(
            username="merchant-lain",
            password="test-password",
        )
        cls.other_merchant.profile.role = UserProfile.Role.MERCHANT
        cls.other_merchant.profile.save(update_fields=("role",))

        cls.product = MerchantProduct.objects.create(
            merchant=cls.merchant,
            product_name="Mystery Bread Box",
            product_stock=5,
            product_status=MerchantProduct.Status.AVAILABLE,
            real_price=Decimal("40000"),
            discount_rate=Decimal("62.50"),
            start_pickup=timezone.now() + timedelta(hours=1),
            end_pickup=timezone.now() + timedelta(hours=3),
            address="Jl. Melati No. 12, Bandung",
        )

    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.client.force_login(self.consumer)

    def create_order(self, status=OrderSystem.PaymentStatus.PENDING):
        claim_code = "SBQR-TEST1234" if status != OrderSystem.PaymentStatus.PENDING else None
        return OrderSystem.objects.create(
            consumer=self.consumer,
            product=self.product,
            quantity=1,
            unit_price=Decimal("15000"),
            total_price=Decimal("15000"),
            payment_status=status,
            claim_qr_code=claim_code,
            pickup_deadline=self.product.end_pickup,
        )

    def test_order_pages_require_login(self):
        self.client.logout()

        response = self.client.get(reverse("main:checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)

    def test_checkout_creates_pending_order_and_reduces_stock(self):
        checkout_started = timezone.now()
        response = self.client.post(
            reverse("main:checkout_product", args=(self.product.pk,)),
            {"quantity": "2"},
        )

        order = OrderSystem.objects.get()
        self.product.refresh_from_db()
        self.assertRedirects(response, reverse("main:payment_detail", args=(order.pk,)))
        self.assertEqual(order.consumer, self.consumer)
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.unit_price, Decimal("15000"))
        self.assertEqual(order.total_price, Decimal("30000"))
        self.assertEqual(order.payment_status, OrderSystem.PaymentStatus.PENDING)
        self.assertTrue(order.payment_qr_id.startswith("SBPAY-"))
        self.assertIsNone(order.claim_qr_code)
        self.assertEqual(order.pickup_deadline, self.product.end_pickup)
        self.assertGreater(order.pickup_deadline, checkout_started)
        self.assertEqual(self.product.product_stock, 3)

    def test_product_exposes_inventory_and_location_contract(self):
        self.assertEqual(self.product.id_inventory, self.product.pk)
        self.assertEqual(self.product.restaurant_id, self.merchant.pk)
        self.assertEqual(self.product.nama_produk, self.product.product_name)
        self.assertEqual(self.product.stok_harian, self.product.product_stock)
        self.assertEqual(self.product.harga_asli, self.product.real_price)
        self.assertEqual(self.product.harga_diskon, self.product.discount_price)
        self.assertEqual(self.product.pickup_address, self.product.address)

    def test_consumer_cannot_open_another_consumers_payment(self):
        order = self.create_order()
        order.consumer = self.other_consumer
        order.save(update_fields=("consumer",))

        response = self.client.get(reverse("main:payment_detail", args=(order.pk,)))

        self.assertEqual(response.status_code, 404)

    def test_expired_pending_payment_restores_stock_once(self):
        order = self.create_order()
        OrderSystem.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=16)
        )
        initial_stock = self.product.product_stock

        self.client.get(reverse("main:payment_detail", args=(order.pk,)))
        self.client.get(reverse("main:payment_detail", args=(order.pk,)))

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.payment_status, OrderSystem.PaymentStatus.EXPIRED)
        self.assertEqual(self.product.product_stock, initial_stock + 1)

    def test_simulator_stores_payment_proof_and_marks_order_paid(self):
        order = self.create_order()
        proof_image = self.payment_image(order)
        self.client.force_login(self.admin)

        scan_response = self.client.post(
            reverse("main:simulator_bayar"),
            {
                "action": "scan",
                "order_id": order.pk,
                "payment_proof": proof_image,
            },
        )
        order.refresh_from_db()
        self.assertEqual(scan_response.status_code, 200)
        self.assertEqual(scan_response.context["order"], order)
        self.assertTrue(order.payment_proof.name.endswith(".png"))

        confirm_response = self.client.post(
            reverse("main:simulator_bayar"),
            {"action": "confirm", "payment_token": scan_response.context["payment_token"]},
        )

        order.refresh_from_db()
        self.assertRedirects(
            confirm_response,
            reverse("main:simulator_bayar"),
        )
        self.assertEqual(order.payment_status, OrderSystem.PaymentStatus.PAID)
        self.assertTrue(order.claim_qr_code.startswith("SBQR-"))

    def test_merchant_validation_completes_order_and_credits_wallet_once(self):
        order = self.create_order(status=OrderSystem.PaymentStatus.PAID)
        self.client.force_login(self.merchant)
        payload = {"action": "confirm", "claim_qr_code": order.claim_qr_code}

        response = self.client.post(reverse("main:validate_claim"), payload)

        order.refresh_from_db()
        wallet = MerchantWallet.objects.get(merchant=self.merchant)
        self.assertRedirects(
            response,
            f"{reverse('main:merchant_orders')}?tab=history&selected={order.pk}",
        )
        self.assertEqual(order.payment_status, OrderSystem.PaymentStatus.COMPLETED)
        self.assertEqual(wallet.balance, order.total_price)

        self.client.post(reverse("main:validate_claim"), payload)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, order.total_price)

    def test_other_merchant_cannot_validate_claim(self):
        order = self.create_order(status=OrderSystem.PaymentStatus.PAID)
        self.client.force_login(self.other_merchant)

        response = self.client.post(
            reverse("main:validate_claim"),
            {"action": "confirm", "claim_qr_code": order.claim_qr_code},
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payment_status, OrderSystem.PaymentStatus.PAID)
        self.assertFalse(MerchantWallet.objects.filter(merchant=self.other_merchant).exists())

    def test_withdrawal_resets_merchant_balance(self):
        MerchantWallet.objects.create(
            merchant=self.merchant,
            balance=Decimal("45000"),
        )
        self.client.force_login(self.merchant)

        response = self.client.post(reverse("main:withdraw_funds"))

        wallet = MerchantWallet.objects.get(merchant=self.merchant)
        self.assertRedirects(response, reverse("main:merchant_orders"))
        self.assertEqual(wallet.balance, Decimal("0"))

    def test_role_specific_dashboards_reject_the_wrong_role(self):
        merchant_response = self.client.get(reverse("main:merchant_orders"))
        self.assertEqual(merchant_response.status_code, 302)

        self.client.force_login(self.merchant)
        consumer_response = self.client.get(reverse("main:order_list"))
        self.assertEqual(consumer_response.status_code, 302)

    def test_merchant_login_redirects_to_merchant_dashboard(self):
        self.client.logout()

        response = self.client.post(
            reverse("main:login"),
            {"username": "roti-kita", "password": "test-password"},
        )

        self.assertRedirects(response, reverse("main:product_view"))

    def payment_image(self, order):
        page = self.client.get(reverse("main:payment_detail", args=(order.pk,)))
        return SimpleUploadedFile(
            "payment.png",
            base64.b64decode(page.context["payment_qr_image"].split(",", 1)[1]),
            content_type="image/png",
        )

    def test_cart_add_update_remove_and_shared_navbar(self):
        response = self.client.get(reverse("main:checkout"))
        self.assertContains(response, "Keranjang masih kosong")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, reverse("main:profile"))
        self.assertRegex(response.content.decode(), r'Contact</a>\s*<a href="/orders/checkout/">Keranjang</a>')
        self.assertNotContains(response, "product-switcher")

        for _ in range(2):
            self.client.get(reverse("main:checkout_product", args=(self.product.pk,)))
        self.assertEqual(self.client.session["order_cart"], {self.product.pk: 1})
        self.client.post(reverse("main:checkout"), {
            "action": "update", f"quantity_{self.product.pk}": 3,
        })
        page = self.client.get(reverse("main:checkout"))
        self.assertEqual(page.context["cart_total"], Decimal("45000"))
        self.assertFalse(OrderSystem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.product_stock, 5)
        self.client.post(reverse("main:checkout"), {"remove_product": self.product.pk})
        self.assertEqual(self.client.session["order_cart"], {})

    def second_product(self):
        return MerchantProduct.objects.create(
            merchant=self.other_merchant, product_name="Coffee Box",
            product_stock=4, real_price=Decimal("50000"), discount_rate=Decimal("50"),
            start_pickup=self.product.start_pickup, end_pickup=self.product.end_pickup,
        )

    def test_multi_product_payment_polling_and_merchant_claims(self):
        coffee = self.second_product()
        for product in (self.product, coffee):
            self.client.get(reverse("main:checkout_product", args=(product.pk,)))
        response = self.client.post(reverse("main:checkout"), {
            f"quantity_{self.product.pk}": 2, f"quantity_{coffee.pk}": 1,
            "total_price": "1",
        })
        orders = list(OrderSystem.objects.order_by("pk"))
        self.assertEqual(len(orders), 2)
        self.assertEqual(sum(order.total_price for order in orders), Decimal("55000"))
        self.assertEqual(self.client.session["order_cart"], {})
        page = self.client.get(response.url)
        self.assertEqual(page.context["payment_total"], Decimal("55000"))
        self.assertNotContains(page, reverse("main:simulator_bayar"))
        proof = self.payment_image(orders[0])
        # A new login can still reopen the entire payment from either order.
        self.client.logout()
        self.client.force_login(self.consumer)
        reopened = self.client.get(reverse("main:payment_detail", args=(orders[1].pk,)))
        self.assertEqual(len(reopened.context["payment_orders"]), 2)
        self.client.force_login(self.admin)
        scan = self.client.post(reverse("main:simulator_bayar"), {
            "action": "scan", "payment_proof": proof,
        })
        self.assertEqual(scan.context["payment_total"], Decimal("55000"))
        payload = {"action": "confirm", "payment_token": scan.context["payment_token"]}
        self.client.post(reverse("main:simulator_bayar"), payload)
        codes = list(OrderSystem.objects.order_by("pk").values_list("claim_qr_code", flat=True))
        self.assertTrue(all(codes))
        self.assertEqual(len(set(codes)), 2)
        self.client.post(reverse("main:simulator_bayar"), payload)
        self.assertEqual(codes, list(OrderSystem.objects.order_by("pk").values_list("claim_qr_code", flat=True)))
        self.client.force_login(self.consumer)
        status = self.client.get(reverse("main:payment_status", args=(orders[0].pk,))).json()
        self.assertEqual(status["status"], "paid")
        self.assertIn(reverse("main:order_list"), status["redirect_url"])
        order = OrderSystem.objects.get(product=self.product)
        self.client.force_login(self.merchant)
        self.client.post(reverse("main:validate_claim"), {
            "action": "confirm", "claim_qr_code": order.claim_qr_code,
        })
        self.assertEqual(MerchantWallet.objects.get(merchant=self.merchant).balance, Decimal("30000"))
        self.assertEqual(OrderSystem.objects.get(product=coffee).payment_status, "paid")

    def test_checkout_validates_entire_cart_before_reserving_any_stock(self):
        coffee = self.second_product()
        for product in (self.product, coffee):
            self.client.get(reverse("main:checkout_product", args=(product.pk,)))
        MerchantProduct.objects.filter(pk=coffee.pk).update(product_stock=0)
        response = self.client.post(reverse("main:checkout"))
        self.assertRedirects(response, reverse("main:checkout"))
        self.assertFalse(OrderSystem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.product_stock, 5)

    def test_simulator_is_admin_only_for_get_and_post(self):
        for user in (self.consumer, self.merchant):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("main:simulator_bayar")).status_code, 403)
            self.assertEqual(self.client.post(reverse("main:simulator_bayar"), {"action": "confirm"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("main:simulator_bayar")).status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("main:simulator_bayar")).status_code, 200)

    def test_simulator_rejects_fake_images_unsigned_qr_and_direct_confirmation(self):
        order = self.create_order()
        blank = BytesIO()
        Image.new("RGB", (200, 200), "white").save(blank, format="PNG")
        unsigned = BytesIO()
        qrcode.make("SISABIJAK-PAY:" + order.payment_qr_id).save(unsigned, format="PNG")
        self.client.force_login(self.admin)
        for content in (b"not-a-picture", blank.getvalue(), unsigned.getvalue()):
            response = self.client.post(reverse("main:simulator_bayar"), {
                "action": "scan",
                "order_id": order.pk,
                "payment_proof": SimpleUploadedFile(order.payment_qr_id + ".png", content, content_type="image/png"),
            })
            self.assertNotIn("payment_token", response.context)
        self.client.post(reverse("main:simulator_bayar"), {
            "action": "confirm", "payment_qr_id": order.payment_qr_id,
        })
        order.refresh_from_db()
        self.assertFalse(order.payment_proof)
        self.assertEqual(order.payment_status, "pending")

    def test_simulator_rejects_changed_amount_and_partial_cart_qr(self):
        coffee = self.second_product()
        for product in (self.product, coffee):
            self.client.get(reverse("main:checkout_product", args=(product.pk,)))
        self.client.post(reverse("main:checkout"))
        order = OrderSystem.objects.order_by("pk").first()
        proof = self.payment_image(order)
        # Even a signed token must describe the whole saved checkout, not one item.
        token = signing.dumps({
            "consumer": self.consumer.pk,
            "items": [[order.payment_qr_id, str(order.total_price)]],
        }, salt="orders.payment")
        partial = BytesIO()
        qrcode.make("SISABIJAK-PAY:" + token).save(partial, format="PNG")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("main:simulator_bayar"), {
            "action": "scan", "payment_proof": SimpleUploadedFile("partial.png", partial.getvalue()),
        })
        self.assertContains(response, "QR tidak cocok")
        OrderSystem.objects.filter(pk=order.pk).update(total_price=Decimal("999"))
        response = self.client.post(reverse("main:simulator_bayar"), {"action": "scan", "payment_proof": proof})
        self.assertContains(response, "QR tidak cocok")
        self.assertFalse(OrderSystem.objects.exclude(payment_status="pending").exists())

    def test_expired_cart_restores_all_stock_once_and_cannot_be_paid(self):
        coffee = self.second_product()
        for product in (self.product, coffee):
            self.client.get(reverse("main:checkout_product", args=(product.pk,)))
        self.client.post(reverse("main:checkout"))
        order = OrderSystem.objects.first()
        proof = self.payment_image(order)
        OrderSystem.objects.update(created_at=timezone.now() - timedelta(minutes=16))
        self.client.force_login(self.admin)
        response = self.client.post(reverse("main:simulator_bayar"), {"action": "scan", "payment_proof": proof})
        self.assertRedirects(response, reverse("main:simulator_bayar"))
        self.assertFalse(OrderSystem.objects.exclude(payment_status="expired").exists())
        self.client.force_login(self.consumer)
        page = self.client.get(reverse("main:payment_detail", args=(order.pk,)))
        self.assertNotContains(page, "data-payment-poll")
        self.product.refresh_from_db()
        coffee.refresh_from_db()
        self.assertEqual(self.product.product_stock, 5)
        self.assertEqual(coffee.product_stock, 4)

    def test_merchant_dashboard_links_and_full_redeem_history(self):
        for _ in range(5):
            self.create_order()
        OrderSystem.objects.update(payment_status="completed")
        self.client.force_login(self.merchant)
        dashboard = self.client.get(reverse("main:product_view"))
        for target in ("main:product_create", "main:merchant_orders", "main:validate_claim"):
            self.assertContains(dashboard, reverse(target))
        incoming = self.client.get(reverse("main:merchant_orders"))
        self.assertEqual(len(incoming.context["displayed_orders"]), 0)
        history = self.client.get(reverse("main:merchant_orders"), {"tab": "history"})
        self.assertEqual(len(history.context["displayed_orders"]), 5)
        for order in OrderSystem.objects.all():
            self.assertContains(history, order.order_number)
        self.client.force_login(self.other_merchant)
        other = self.client.get(reverse("main:merchant_orders"), {"tab": "history"})
        self.assertEqual(len(other.context["displayed_orders"]), 0)


class UserRoleTests(TestCase):
    def test_new_web_user_is_consumer(self):
        user = User.objects.create_user(username="consumer", password="password123")
        self.assertEqual(user.profile.role, UserProfile.Role.CONSUMER)

    def test_consumer_cannot_access_merchant_dashboard(self):
        user = User.objects.create_user(username="consumer", password="password123")
        self.client.force_login(user)
        response = self.client.get(reverse("main:product_view"))
        self.assertRedirects(response, reverse("main:show_main"))

    def test_merchant_can_access_merchant_dashboard(self):
        user = User.objects.create_user(username="merchant", password="password123")
        user.profile.role = UserProfile.Role.MERCHANT
        user.profile.save()
        self.client.force_login(user)
        response = self.client.get(reverse("main:product_view"))
        self.assertEqual(response.status_code, 200)


class ConsumerProfileTests(TestCase):
    def setUp(self):
        self.consumer = User.objects.create_user(
            username="consumer_profile_test",
            password="OldPassword123!",
        )
        self.client.force_login(self.consumer)

    def test_consumer_can_open_edit_profile_page(self):
        response = self.client.get(reverse("main:edit_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "edit_profile_view.html")
        self.assertIn("profile_form", response.context)
        self.assertIn("password_form", response.context)

    def test_merchant_cannot_open_consumer_edit_profile_page(self):
        merchant = User.objects.create_user(
            username="merchant_profile_test",
            password="OldPassword123!",
        )
        merchant.profile.role = UserProfile.Role.MERCHANT
        merchant.profile.save()

        self.client.force_login(merchant)
        response = self.client.get(reverse("main:edit_profile"))

        self.assertRedirects(response, reverse("main:show_main"))


class ConsumerPasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="password_change_test",
            password="OldPassword123!",
        )
        self.client.force_login(self.user)

    def test_consumer_can_change_password(self):
        response = self.client.post(
            reverse("main:edit_profile"),
            {
                "action": "password",
                "old_password": "OldPassword123!",
                "new_password1": "NewPassword456!Secure",
                "new_password2": "NewPassword456!Secure",
            },
        )

        self.user.refresh_from_db()
        self.assertTrue(
            self.user.check_password("NewPassword456!Secure")
        )
        self.assertFalse(
            self.user.check_password("OldPassword123!")
        )

