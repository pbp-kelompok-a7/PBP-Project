from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4


def generate_product_id():
    return f"PRD-{uuid4().hex[:12].upper()}"


class UserProfile(models.Model):
    """Peran aplikasi untuk akun yang sudah terautentikasi."""

    class Role(models.TextChoices):
        CONSUMER = "consumer", "Consumer"
        MERCHANT = "merchant", "Merchant"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CONSUMER)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class MerchantProduct(models.Model):
    """Produk surplus yang diunggah dan dikelola oleh satu merchant."""

    class ProductStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        SOLD_OUT = "sold_out", "Sold Out"
        INACTIVE = "inactive", "Inactive"

    product_id = models.CharField(
        max_length=20, primary_key=True, default=generate_product_id, editable=False
    )
    merchant = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="merchant_products"
    )
    product_name = models.CharField(max_length=150)
    product_stock = models.PositiveIntegerField(default=0)
    product_status = models.CharField(
        max_length=10, choices=ProductStatus.choices, default=ProductStatus.AVAILABLE
    )
    real_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    start_pickup = models.DateTimeField()
    end_pickup = models.DateTimeField()

    class Meta:
        ordering = ["start_pickup", "product_name"]

    def __str__(self):
        return self.product_name

    @property
    def discount_price(self):
        """Harga jual setelah diskon, selalu dihitung dari harga asli dan rate."""
        multiplier = Decimal("1") - (self.discount_rate / Decimal("100"))
        return (self.real_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
