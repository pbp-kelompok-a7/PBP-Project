from django.db import migrations


def create_order_roles(apps, schema_editor):
    group = apps.get_model("auth", "Group")
    group.objects.get_or_create(name="Consumer")
    group.objects.get_or_create(name="Merchant")


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_order_roles, migrations.RunPython.noop),
    ]
