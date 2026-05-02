import os

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from src.users.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Create / update subscription plans for Lemon Squeezy."

    def handle(self, *args, **kwargs):
        # Deactivate legacy daily plan if present
        daily = SubscriptionPlan.objects.filter(slug="daily-hero").first()
        if daily and daily.is_active:
            daily.is_active = False
            daily.save(update_fields=["is_active"])
            self.stdout.write(self.style.WARNING("Deactivated legacy: Daily Hero"))

        plans_data = [
            {
                "name": _("Monthly Hero Access"),
                "slug": "monthly-hero",
                "description": "",
                "price": "7.99",
                "currency": "USD",
                "duration_days": 30,
                "is_lifetime": False,
                "ls_variant_id": os.environ.get("LS_VARIANT_MONTHLY", ""),
            },
            {
                "name": _("Yearly Hero Access"),
                "slug": "yearly-hero",
                "description": "",
                "price": "79.00",
                "currency": "USD",
                "duration_days": 365,
                "is_lifetime": False,
                "ls_variant_id": os.environ.get("LS_VARIANT_YEARLY", ""),
            },
            {
                "name": _("Lifetime Hero Access (Founder's Deal)"),
                "slug": "lifetime-hero",
                "description": _("One-time payment. Limited to first 100 customers."),
                "price": "129.00",
                "currency": "USD",
                "duration_days": 0,
                "is_lifetime": True,
                "ls_variant_id": os.environ.get("LS_VARIANT_LIFETIME", ""),
            },
        ]

        for data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                slug=data["slug"], defaults=data
            )
            if not created:
                for k, v in data.items():
                    if k == "slug":
                        continue
                    setattr(plan, k, v)
                plan.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Created' if created else 'Updated'}: {plan.name}"
                )
            )
