from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from src.users.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Create initial subscription plans"

    def handle(self, *args, **kwargs):
        plans_data = [
            {
                "name": _("Daily Hero Access"),
                "slug": "daily-hero",
                "description": "",
                "price": 1.00,
                "currency": "USD",
                "duration_days": 1,
            },
            {
                "name": _("Monthly Hero Access"),
                "slug": "monthly-hero",
                "description": "",
                "price": 6.00,
                "currency": "USD",
                "duration_days": 30,
            },
            {
                "name": _("Yearly Hero Access"),
                "slug": "yearly-hero",
                "description": "",
                "price": 52.00,
                "currency": "USD",
                "duration_days": 365,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                slug=plan_data["slug"], defaults=plan_data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Update existing plan
                for key, value in plan_data.items():
                    if key != "slug":
                        setattr(plan, key, value)
                plan.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated plan: {plan.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {created_count} plans created, "
                f"{updated_count} plans updated. "
                f"Total plans: {SubscriptionPlan.objects.count()}"
            )
        )
