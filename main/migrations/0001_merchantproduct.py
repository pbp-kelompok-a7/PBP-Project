"""Bridge the older Order System product table to the shared merchant contract."""

from datetime import datetime, timedelta

import main.models
from django.db import migrations, models
from django.utils import timezone


def preserve_pickup_times(apps, schema_editor):
    Product = apps.get_model("main", "MerchantProduct")
    now = timezone.now()
    for product in Product.objects.all():
        pickup_date = timezone.localdate(now)
        start = timezone.make_aware(datetime.combine(pickup_date, product.start_pickup))
        end = timezone.make_aware(datetime.combine(pickup_date, product.end_pickup))
        if end <= start:
            end += timedelta(days=1)
        if end <= now:
            start += timedelta(days=1)
            end += timedelta(days=1)
        Product.objects.filter(pk=product.pk).update(
            pickup_start_at=start,
            pickup_end_at=end,
        )


class Migration(migrations.Migration):
    dependencies = [("main", "0003_ordersystem_payment_proof")]

    operations = [
        migrations.RenameField("MerchantProduct", "id", "product_id"),
        migrations.AlterField(
            "MerchantProduct",
            "product_id",
            models.CharField(
                max_length=20,
                primary_key=True,
                default=main.models.generate_product_id,
                editable=False,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            "MerchantProduct", "product_name", models.CharField(max_length=150)
        ),
        migrations.AddField(
            "MerchantProduct", "pickup_start_at", models.DateTimeField(null=True)
        ),
        migrations.AddField(
            "MerchantProduct", "pickup_end_at", models.DateTimeField(null=True)
        ),
        migrations.RunPython(preserve_pickup_times, migrations.RunPython.noop),
        migrations.RemoveField("MerchantProduct", "start_pickup"),
        migrations.RemoveField("MerchantProduct", "end_pickup"),
        migrations.RenameField("MerchantProduct", "pickup_start_at", "start_pickup"),
        migrations.RenameField("MerchantProduct", "pickup_end_at", "end_pickup"),
        migrations.AlterField("MerchantProduct", "start_pickup", models.DateTimeField()),
        migrations.AlterField("MerchantProduct", "end_pickup", models.DateTimeField()),
        migrations.AlterModelOptions(
            "MerchantProduct", options={"ordering": ("start_pickup", "product_name")}
        ),
    ]
