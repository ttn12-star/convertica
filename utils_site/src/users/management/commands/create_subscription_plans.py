from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from src.users.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Create initial subscription plans"

    def handle(self, *args, **kwargs):
        # Keep legacy daily plans unavailable.
        daily_plan = SubscriptionPlan.objects.filter(slug="daily-hero").first()
        if daily_plan and daily_plan.is_active:
            daily_plan.is_active = False
            daily_plan.save(update_fields=["is_active"])
            self.stdout.write(
                self.style.WARNING("Deactivated legacy plan: Daily Hero Access")
            )

        plans_data = [
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
                "price": 59.00,
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
