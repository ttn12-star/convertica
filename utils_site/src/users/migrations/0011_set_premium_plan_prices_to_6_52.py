from decimal import Decimal

from django.db import migrations


def _update_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("users", "SubscriptionPlan")

    updates = {
        "daily-hero": Decimal("1.00"),
        "monthly-hero": Decimal("6.00"),
        "yearly-hero": Decimal("52.00"),
    }

    for slug, price in updates.items():
        SubscriptionPlan.objects.filter(slug=slug).update(price=price, currency="USD")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_rename_users_oprun_conv_created_idx_users_opera_convers_d70162_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(_update_plans, migrations.RunPython.noop),
    ]
