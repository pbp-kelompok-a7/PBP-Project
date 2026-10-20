# Generated manually for MerchantProduct.

import django.db.models.deletion
import main.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MerchantProduct",
            fields=[
                ("product_id", models.CharField(default=main.models.generate_product_id, editable=False, max_length=20, primary_key=True, serialize=False)),
                ("product_name", models.CharField(max_length=150)),
                ("product_stock", models.PositiveIntegerField(default=0)),
                ("product_status", models.CharField(choices=[("available", "Available"), ("sold_out", "Sold Out"), ("inactive", "Inactive")], default="available", max_length=10)),
                ("real_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("discount_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("start_pickup", models.DateTimeField()),
                ("end_pickup", models.DateTimeField()),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="merchant_products", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["start_pickup", "product_name"]},
        ),
    ]
