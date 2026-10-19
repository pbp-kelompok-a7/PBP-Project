from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
from django.core.validators import MaxValueValidator, MinValueValidator


def convert_discount_prices_to_rates(apps, schema_editor):
    MerchantProduct = apps.get_model("main", "MerchantProduct")
    for product in MerchantProduct.objects.all():
        if product.real_price > 0:
            rate = (Decimal("100") * (product.real_price - product.discount_price) / product.real_price)
            product.discount_rate = min(Decimal("100"), max(Decimal("0"), rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))
        else:
            product.discount_rate = Decimal("0")
        product.save(update_fields=["discount_rate"])


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0002_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="merchantproduct",
            name="discount_rate",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5),
        ),
        migrations.RunPython(convert_discount_prices_to_rates, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="merchantproduct",
            name="discount_price",
        ),
        migrations.AlterField(
            model_name="merchantproduct",
            name="discount_rate",
            field=models.DecimalField(decimal_places=2, help_text="Masukkan persentase diskon dari 0 sampai 100.", max_digits=5, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]),
        ),
    ]
