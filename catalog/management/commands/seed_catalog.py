import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from main.models import MerchantProduct, OrderSystem, UserProfile

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "paket_dummy.json"
# folder foto contoh, nama file = nama produk versi slug (misal croissant.jpg)
FOTO_DIR = Path(__file__).resolve().parents[2] / "data" / "foto"
FOTO_EXT = [".jpg", ".jpeg", ".png", ".webp"]

STATUS_MAP = {
    "Available": MerchantProduct.ProductStatus.AVAILABLE,
    "Sold Out": MerchantProduct.ProductStatus.SOLD_OUT,
    "Inactive": MerchantProduct.ProductStatus.INACTIVE,
}


def jam_hari_ini(teks):
    # "20:00" -> datetime hari ini jam 20:00 (zona waktu Jakarta)
    jam, menit = map(int, teks.split(":"))
    hari_ini = timezone.localdate()
    return timezone.make_aware(datetime(hari_ini.year, hari_ini.month, hari_ini.day, jam, menit))


class Command(BaseCommand):
    help = "Isi database dengan 50 produk dari catalog/data/paket_dummy.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-consumer",
            help="username consumer yang dikasih 3 order completed, buat ngetes fitur review",
        )

    def handle(self, *args, **options):
        with open(DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)

        jumlah_produk = 0
        jumlah_foto = 0
        for item in data:
            merchant = self.ambil_merchant(item["name_merchant"])

            real_price = Decimal(item["real_price"])
            discount_price = Decimal(item["discount_price"])
            # model jefry nyimpen persen diskon, jadi diitung dari harga asli & harga diskon
            discount_rate = (1 - discount_price / real_price) * 100
            if discount_rate != discount_rate.quantize(Decimal("0.01")):
                # kalau persennya ga bulet (misal 66.666...), dibuletin ke persen terdekat
                # biar harga diskonnya ga jadi aneh kayak Rp19.998
                discount_rate = discount_rate.quantize(Decimal("1"))
            discount_rate = discount_rate.quantize(Decimal("0.01"))

            start_pickup = jam_hari_ini(item["start_pickup"])
            end_pickup = jam_hari_ini(item["end_pickup"])
            if end_pickup <= timezone.now() + timedelta(minutes=15):
                # kalau jam pickup hari ini udah lewat, pindahin ke besok biar masih bisa di-checkout
                start_pickup += timedelta(days=1)
                end_pickup += timedelta(days=1)

            nama = item["product_name"]
            # dulu nama produknya pake "Box" (misal "Croissant Box"), produk yang namanya
            # masih versi lama diganti dulu biar pas di-seed ulang ga jadi dobel
            nama_lama = "Rice Box Surprise" if nama == "Rice Surprise" else f"{nama} Box"
            MerchantProduct.objects.filter(merchant=merchant, product_name=nama_lama).update(product_name=nama)

            produk, _ = MerchantProduct.objects.update_or_create(
                merchant=merchant,
                product_name=nama,
                defaults={
                    "product_stock": item["product_stock"],
                    "product_status": STATUS_MAP[item["product_status"]],
                    "real_price": real_price,
                    "discount_rate": discount_rate,
                    "start_pickup": start_pickup,
                    "end_pickup": end_pickup,
                    "address": item["address"],
                },
            )
            jumlah_produk += 1
            if self.pasang_foto(produk):
                jumlah_foto += 1

        self.stdout.write(self.style.SUCCESS(f"{jumlah_produk} produk berhasil di-seed ({jumlah_foto} foto baru)"))

        if options["demo_consumer"]:
            self.bikin_order_demo(options["demo_consumer"])

    def pasang_foto(self, produk):
        # Jika produk punya foto DAN file fisiknya benar-benar ada di storage, jangan timpa
        if produk.product_photo:
            try:
                if produk.product_photo.storage.exists(produk.product_photo.name):
                    return False
            except Exception:
                pass

        # Jika file fisiknya belum ada (misal setelah redeploy container baru),
        # salin ulang foto dari catalog/data/foto/
        nama = slugify(produk.product_name)
        for ext in FOTO_EXT:
            path = FOTO_DIR / f"{nama}{ext}"
            if path.exists():
                with open(path, "rb") as f:
                    produk.product_photo.save(f"{nama}{ext}", File(f), save=True)
                return True
        return False

    def ambil_merchant(self, nama_toko):
        # 1 toko = 1 akun merchant, nama toko disimpen di first_name
        merchant, dibuat = User.objects.get_or_create(
            username=slugify(nama_toko),
            defaults={"first_name": nama_toko},
        )
        if dibuat:
            # akun merchant hasil seed ga bisa login, passwordnya diset admin kalau perlu
            merchant.set_unusable_password()
            merchant.save()
        profile, _ = UserProfile.objects.get_or_create(user=merchant)
        if profile.role != UserProfile.Role.MERCHANT:
            profile.role = UserProfile.Role.MERCHANT
            profile.save()
        return merchant

    def bikin_order_demo(self, username):
        try:
            consumer = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' ga ketemu, register dulu lewat web")

        produk_list = MerchantProduct.objects.filter(
            product_status=MerchantProduct.ProductStatus.AVAILABLE
        ).order_by("-discount_rate", "product_name")[:3]

        for produk in produk_list:
            sudah_ada = OrderSystem.objects.filter(
                consumer=consumer,
                product=produk,
                payment_status=OrderSystem.PaymentStatus.COMPLETED,
            ).exists()
            if sudah_ada:
                continue
            OrderSystem.objects.create(
                consumer=consumer,
                product=produk,
                quantity=1,
                unit_price=produk.discount_price,
                total_price=produk.discount_price,
                payment_status=OrderSystem.PaymentStatus.COMPLETED,
                pickup_deadline=timezone.now() + timedelta(hours=1),
            )

        nama = ", ".join(p.product_name for p in produk_list)
        self.stdout.write(self.style.SUCCESS(f"Order completed buat {username}: {nama}"))