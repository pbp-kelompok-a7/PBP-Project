from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import MerchantProduct, UserProfile


class Command(BaseCommand):
    help = "Membuat akun consumer, merchant, dan produk lokal untuk mencoba Order System."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Password untuk akun demo yang baru dibuat.",
        )
        parser.add_argument("--consumer", default="consumer_demo")
        parser.add_argument("--merchant", default="merchant_demo")

    def handle(self, *args, **options):
        consumer, consumer_created = User.objects.get_or_create(
            username=options["consumer"]
        )
        merchant, merchant_created = User.objects.get_or_create(
            username=options["merchant"]
        )

        if consumer_created:
            consumer.set_password(options["password"])
            consumer.first_name = "Ayu"
            consumer.last_name = "Lestari"
            consumer.save()
        UserProfile.objects.update_or_create(
            user=consumer, defaults={"role": UserProfile.Role.CONSUMER}
        )

        if merchant_created:
            merchant.set_password(options["password"])
            merchant.first_name = "Roti Kita Bakery"
            merchant.save()
        UserProfile.objects.update_or_create(
            user=merchant, defaults={"role": UserProfile.Role.MERCHANT}
        )

        product, product_created = MerchantProduct.objects.get_or_create(
            merchant=merchant,
            product_name="Mystery Bread Box",
            defaults={
                "product_stock": 10,
                "product_status": MerchantProduct.Status.AVAILABLE,
                "real_price": Decimal("40000"),
                "discount_rate": Decimal("62.50"),
                "start_pickup": timezone.now() + timedelta(hours=1),
                "end_pickup": timezone.now() + timedelta(hours=3),
                "address": "Jl. Melati No. 12, Bandung",
            },
        )

        self.stdout.write(self.style.SUCCESS("Data demo Order System siap."))
        self.stdout.write(f"Consumer: {consumer.username}")
        self.stdout.write(f"Merchant: {merchant.username}")
        self.stdout.write(f"Produk: {product.product_name} (id={product.pk})")
        if not consumer_created or not merchant_created:
            self.stdout.write(
                self.style.WARNING(
                    "Akun yang sudah ada tidak diubah password-nya. Gunakan password lama akun tersebut."
                )
            )
        if not product_created:
            self.stdout.write("Produk demo yang sudah ada dipakai kembali tanpa mengubah datanya.")
