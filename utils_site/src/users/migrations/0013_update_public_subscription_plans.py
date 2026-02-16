from decimal import Decimal

from django.db import migrations


def update_public_subscription_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("users", "SubscriptionPlan")

    SubscriptionPlan.objects.filter(slug="daily-hero").update(is_active=False)
    SubscriptionPlan.objects.filter(slug="monthly-hero").update(
        price=Decimal("6.00"),
        duration_days=30,
        currency="USD",
    )
    SubscriptionPlan.objects.filter(slug="yearly-hero").update(
        price=Decimal("59.00"),
        duration_days=365,
        currency="USD",
    )


def reverse_public_subscription_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("users", "SubscriptionPlan")

    SubscriptionPlan.objects.filter(slug="daily-hero").update(is_active=True)
    SubscriptionPlan.objects.filter(slug="yearly-hero").update(price=Decimal("52.00"))


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0012_runtimesetting"),
    ]

    operations = [
        migrations.RunPython(
            update_public_subscription_plans,
            reverse_public_subscription_plans,
        ),
    ]
