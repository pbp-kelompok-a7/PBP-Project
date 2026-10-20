"""Finish the merchant product contract without recreating Order System tables."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("main", "0004_remove_discount_rate_help_text")]

    operations = [
        migrations.AlterField(
            model_name="merchantproduct",
            name="product_status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("sold_out", "Sold Out"),
                    ("inactive", "Inactive"),
                ],
                default="available",
                max_length=16,
            ),
        ),
    ]
