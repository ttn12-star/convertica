"""Align public plan prices with the create_subscription_plans seed values.

Migration 0013 set monthly=$6.00 / yearly=$59.00, while the seed command
(create_subscription_plans) says $7.99 / $79.00 — which is what LemonSqueezy
actually charges. Whichever ran last won, so prod display could disagree
with the real charge. Pin the seed values deterministically.
"""

from decimal import Decimal

from django.db import migrations


def align_prices(apps, schema_editor):
    SubscriptionPlan = apps.get_model("users", "SubscriptionPlan")
    for slug, price in {
        "monthly-hero": Decimal("7.99"),
        "yearly-hero": Decimal("79.00"),
        "lifetime-hero": Decimal("129.00"),
    }.items():
        SubscriptionPlan.objects.filter(slug=slug).update(price=price)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0028_pushsubscription"),
    ]

    operations = [
        migrations.RunPython(align_prices, migrations.RunPython.noop),
    ]
