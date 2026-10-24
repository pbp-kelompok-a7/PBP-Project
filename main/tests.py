from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import MerchantProduct, MerchantWallet, OrderSystem, UserProfile


class OrderSystemFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        proof_image = SimpleUploadedFile(
            "bukti-transfer.png",
            b"dummy-png-content",
            content_type="image/png",
        )

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
        self.assertIn("bukti-transfer", order.payment_proof.name)

        confirm_response = self.client.post(
            reverse("main:simulator_bayar"),
            {"action": "confirm", "payment_qr_id": order.payment_qr_id},
        )

        order.refresh_from_db()
        self.assertRedirects(
            confirm_response,
            f"{reverse('main:order_list')}?highlight={order.pk}",
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
            f"{reverse('main:merchant_orders')}?selected={order.pk}",
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

        self.assertRedirects(response, reverse("main:merchant_orders"))


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
