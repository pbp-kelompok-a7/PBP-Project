from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0003_discount_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="merchantproduct",
            name="discount_rate",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=5,
                validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
            ),
        ),
    ]
