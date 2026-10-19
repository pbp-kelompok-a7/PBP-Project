import secrets
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone


def generate_payment_qr_id():
    return f"SBPAY-{secrets.token_hex(6).upper()}"


def generate_claim_qr_code():
    return f"SBQR-{secrets.token_hex(4).upper()}"


def payment_proof_upload_to(instance, filename):
    safe_filename = Path(filename).name
    return (
        f"payment_proofs/{instance.consumer_id}/"
        f"{instance.payment_qr_id}/{safe_filename}"
    )


class MerchantProduct(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Tersedia"
        SOLD_OUT = "sold_out", "Habis"
        INACTIVE = "inactive", "Nonaktif"

    merchant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="merchant_products",
    )
    product_name = models.CharField(max_length=120)
    product_stock = models.PositiveIntegerField(default=0)
    product_status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    real_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2)
    start_pickup = models.TimeField()
    end_pickup = models.TimeField()
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("product_name",)

    def __str__(self):
        return f"{self.product_name} - {self.merchant.username}"

    def clean(self):
        if self.discount_price > self.real_price:
            raise ValidationError(
                {"discount_price": "Harga diskon tidak boleh melebihi harga asli."}
            )
        if self.start_pickup >= self.end_pickup:
            raise ValidationError(
                {"end_pickup": "Jam selesai pickup harus setelah jam mulai."}
            )

    @property
    def discount_percentage(self):
        if not self.real_price:
            return 0
        return round((1 - self.discount_price / self.real_price) * 100)

    # Alias berikut mengikuti kontrak atribut modul Merchant Inventory di README.
    # Model sementara ini dapat diganti oleh MerchantInventory tanpa mengubah template.
    @property
    def id_inventory(self):
        return self.pk

    @property
    def restaurant_id(self):
        return self.merchant_id

    @property
    def nama_produk(self):
        return self.product_name

    @property
    def stok_harian(self):
        return self.product_stock

    @property
    def harga_asli(self):
        return self.real_price

    @property
    def harga_diskon(self):
        return self.discount_price

    @property
    def jam_mulai_pickup(self):
        return self.start_pickup

    @property
    def jam_selesai_pickup(self):
        return self.end_pickup

    @property
    def status(self):
        return self.product_status

    @property
    def merchant_name(self):
        return self.merchant.get_full_name() or self.merchant.username

    @property
    def pickup_address(self):
        """Prioritaskan alamat dari modul lokasi bila relasinya sudah tersedia."""

        for relation_name in ("merchant_location", "merchantlocation", "location"):
            try:
                location = getattr(self.merchant, relation_name)
            except (AttributeError, ObjectDoesNotExist):
                continue
            location_address = getattr(location, "address", "")
            if location_address:
                return location_address
        return self.address


class OrderSystem(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Menunggu pembayaran"
        PAID = "paid", "Siap diklaim"
        COMPLETED = "completed", "Selesai"
        EXPIRED = "expired", "Kedaluwarsa"

    consumer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="consumer_orders",
    )
    product = models.ForeignKey(
        MerchantProduct,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    payment_qr_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_payment_qr_id,
        editable=False,
    )
    payment_proof = models.FileField(
        upload_to=payment_proof_upload_to,
        null=True,
        blank=True,
    )
    claim_qr_code = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    pickup_deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.order_number} - {self.consumer.username}"

    def clean(self):
        if self.quantity < 1:
            raise ValidationError({"quantity": "Jumlah pesanan minimal satu."})
        expected_total = Decimal(self.unit_price) * self.quantity
        if self.total_price != expected_total:
            raise ValidationError(
                {"total_price": "Total harga harus sama dengan harga satuan x jumlah."}
            )

    @property
    def order_number(self):
        created = (
            timezone.localtime(self.created_at)
            if self.created_at
            else timezone.localtime()
        )
        suffix = f"{self.pk:03d}" if self.pk else "NEW"
        return f"SB-{created:%y%m%d}-{suffix}"

    @property
    def payment_deadline(self):
        return self.created_at + timedelta(minutes=15)

    @property
    def is_payment_expired(self):
        return (
            self.payment_status == self.PaymentStatus.PENDING
            and timezone.now() >= self.payment_deadline
        )

    @property
    def is_pickup_expired(self):
        return (
            self.payment_status == self.PaymentStatus.PAID
            and timezone.now() >= self.pickup_deadline
        )

    def mark_paid(self):
        if self.payment_status != self.PaymentStatus.PENDING:
            raise ValidationError("Hanya pesanan pending yang dapat dibayar.")
        if self.is_payment_expired:
            raise ValidationError("Waktu pembayaran pesanan sudah habis.")
        self.payment_status = self.PaymentStatus.PAID
        self.claim_qr_code = generate_claim_qr_code()
        self.save(update_fields=("payment_status", "claim_qr_code"))


class MerchantWallet(models.Model):
    merchant = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="merchant_wallet",
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Saldo {self.merchant.username}: {self.balance}"
