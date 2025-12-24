from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from src.users.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Create initial subscription plans"

    def handle(self, *args, **kwargs):
        plans_data = [
            {
                "name": _("Daily Hero Access"),
                "plan_type": "daily",
                "price": 1.00,
                "duration_days": 1,
                "features": [
                    _("Unlimited conversions for 24 hours"),
                    _("No file size limits"),
                    _("Priority processing"),
                    _("Ad-free experience"),
                ],
            },
            {
                "name": _("Monthly Hero Access"),
                "plan_type": "monthly",
                "price": 6.00,
                "duration_days": 30,
                "features": [
                    _("Everything in Daily, plus:"),
                    _("Batch processing (up to 10 files)"),
                    _("OCR text recognition"),
                    _("Cloud storage (5GB, 7 days)"),
                    _("API access (1000 requests/month)"),
                ],
            },
            {
                "name": _("Yearly Hero Access"),
                "plan_type": "yearly",
                "price": 52.00,
                "duration_days": 365,
                "features": [
                    _("Everything in Monthly, plus:"),
                    _("Unlimited batch processing"),
                    _("Priority support"),
                    _("Advanced OCR features"),
                    _("Hero badge on profile"),
                ],
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data["plan_type"], defaults=plan_data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Update existing plan
                for key, value in plan_data.items():
                    if key != "plan_type":
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
