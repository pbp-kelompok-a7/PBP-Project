import django.db.models.deletion
import main.models
from django.conf import settings
from django.db import migrations, models


def prepare_order_tables(apps, schema_editor):
    """Gunakan tabel lama orders bila ada, atau buat tabel main pada instalasi baru."""

    table_names = set(schema_editor.connection.introspection.table_names())
    table_map = (
        ("MerchantProduct", "orders_merchantproduct"),
        ("MerchantWallet", "orders_merchantwallet"),
        ("OrderSystem", "orders_ordersystem"),
    )

    for model_name, old_table_name in table_map:
        model = apps.get_model("main", model_name)
        new_table_name = model._meta.db_table

        if new_table_name in table_names:
            continue
        if old_table_name in table_names:
            schema_editor.alter_db_table(model, old_table_name, new_table_name)
            table_names.remove(old_table_name)
        else:
            schema_editor.create_model(model)
        table_names.add(new_table_name)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="MerchantProduct",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("product_name", models.CharField(max_length=120)),
                        ("product_stock", models.PositiveIntegerField(default=0)),
                        (
                            "product_status",
                            models.CharField(
                                choices=[
                                    ("available", "Tersedia"),
                                    ("sold_out", "Habis"),
                                    ("inactive", "Nonaktif"),
                                ],
                                default="available",
                                max_length=16,
                            ),
                        ),
                        (
                            "real_price",
                            models.DecimalField(decimal_places=2, max_digits=12),
                        ),
                        (
                            "discount_price",
                            models.DecimalField(decimal_places=2, max_digits=12),
                        ),
                        ("start_pickup", models.TimeField()),
                        ("end_pickup", models.TimeField()),
                        ("address", models.CharField(blank=True, max_length=255)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "merchant",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="merchant_products",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={"ordering": ("product_name",)},
                ),
                migrations.CreateModel(
                    name="MerchantWallet",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "balance",
                            models.DecimalField(
                                decimal_places=2,
                                default=0,
                                max_digits=14,
                            ),
                        ),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "merchant",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="merchant_wallet",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    name="OrderSystem",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("quantity", models.PositiveIntegerField()),
                        (
                            "unit_price",
                            models.DecimalField(decimal_places=2, max_digits=12),
                        ),
                        (
                            "total_price",
                            models.DecimalField(decimal_places=2, max_digits=12),
                        ),
                        (
                            "payment_status",
                            models.CharField(
                                choices=[
                                    ("pending", "Menunggu pembayaran"),
                                    ("paid", "Siap diklaim"),
                                    ("completed", "Selesai"),
                                    ("expired", "Kedaluwarsa"),
                                ],
                                db_index=True,
                                default="pending",
                                max_length=16,
                            ),
                        ),
                        (
                            "payment_qr_id",
                            models.CharField(
                                default=main.models.generate_payment_qr_id,
                                editable=False,
                                max_length=32,
                                unique=True,
                            ),
                        ),
                        (
                            "claim_qr_code",
                            models.CharField(
                                blank=True,
                                editable=False,
                                max_length=32,
                                null=True,
                                unique=True,
                            ),
                        ),
                        ("pickup_deadline", models.DateTimeField()),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "consumer",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="consumer_orders",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "product",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="orders",
                                to="main.merchantproduct",
                            ),
                        ),
                    ],
                    options={"ordering": ("-created_at",)},
                ),
            ],
        ),
        migrations.RunPython(prepare_order_tables, migrations.RunPython.noop),
    ]
