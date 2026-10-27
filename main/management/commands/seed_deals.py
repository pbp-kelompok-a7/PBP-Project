from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import MerchantProduct, UserProfile

# username, nama tampil merchant, nama produk, harga asli, diskon (%), stok, alamat
SAMPLES = [
    ("nori_corner", "Nori Corner", "5 Jus Pilihan", 85000, 60, 4, "Jl. Kemakmuran No. 5, Depok"),
    ("kopi_senja", "Kopi Senja Cafe", "Pastry Box", 45000, 50, 6, "Jl. Beji Timur No. 3, Depok"),
    ("sweet_crumbs", "Sweet Crumbs", "Donut Box", 48000, 40, 5, "Jl. Haji Asmawi No. 8, Depok"),
]


class Command(BaseCommand):
    help = "Isi produk contoh agar Diskon Hari Ini di halaman depan tampil 4 kartu."

    def handle(self, *args, **options):
        now = timezone.now()

        for username, merchant_name, product_name, price, rate, stock, address in SAMPLES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": merchant_name},
            )
            if created:
                user.set_unusable_password()
                user.save()

            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": UserProfile.Role.MERCHANT},
            )

            MerchantProduct.objects.update_or_create(
                merchant=user,
                product_name=product_name,
                defaults={
                    "product_stock": stock,
                    "product_status": MerchantProduct.Status.AVAILABLE,
                    "real_price": Decimal(price),
                    "discount_rate": Decimal(rate),
                    "start_pickup": now + timedelta(hours=1),
                    "end_pickup": now + timedelta(hours=9),
                    "address": address,
                },
            )
            self.stdout.write(f"OK: {product_name} ({merchant_name})")

        self.stdout.write(self.style.SUCCESS("Selesai. Muat ulang halaman depan."))