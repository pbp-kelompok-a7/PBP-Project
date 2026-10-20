import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("main", "UserProfile")
    MerchantProduct = apps.get_model("main", "MerchantProduct")
    for user in User.objects.all():
        is_merchant = user.groups.filter(name__in=("Merchant", "Restaurant")).exists()
        is_merchant = is_merchant or MerchantProduct.objects.filter(merchant_id=user.pk).exists()
        UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": "merchant" if is_merchant else "consumer"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0001_merchantproduct"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("consumer", "Consumer"), ("merchant", "Merchant")], default="consumer", max_length=10)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(create_profiles_for_existing_users, migrations.RunPython.noop),
    ]
