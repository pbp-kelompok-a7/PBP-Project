from datetime import time
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from main.models import MerchantProduct


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
        consumer_group, _ = Group.objects.get_or_create(name="Consumer")
        merchant_group, _ = Group.objects.get_or_create(name="Merchant")

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
        consumer.groups.add(consumer_group)

        if merchant_created:
            merchant.set_password(options["password"])
            merchant.first_name = "Roti Kita Bakery"
            merchant.save()
        merchant.groups.add(merchant_group)

        product, product_created = MerchantProduct.objects.get_or_create(
            merchant=merchant,
            product_name="Mystery Bread Box",
            defaults={
                "product_stock": 10,
                "product_status": MerchantProduct.Status.AVAILABLE,
                "real_price": Decimal("40000"),
                "discount_price": Decimal("15000"),
                "start_pickup": time(20, 0),
                "end_pickup": time(21, 0),
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
