from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from src.users.models import SubscriptionPlan


class CreateSubscriptionPlansTests(TestCase):
    def test_creates_monthly_and_yearly_only(self):
        call_command("create_subscription_plans")
        slugs = set(SubscriptionPlan.objects.values_list("slug", flat=True))
        self.assertIn("monthly-hero", slugs)
        self.assertIn("yearly-hero", slugs)
        # Lifetime is retired — the seed must never (re)create it.
        self.assertNotIn("lifetime-hero", slugs)

    def test_existing_lifetime_is_deactivated(self):
        # A lingering active lifetime plan (seeded before retirement) must be
        # pulled from sale when the command runs.
        SubscriptionPlan.objects.create(
            name="Lifetime Hero Access",
            slug="lifetime-hero",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            is_active=True,
        )
        call_command("create_subscription_plans")
        lifetime = SubscriptionPlan.objects.get(slug="lifetime-hero")
        self.assertFalse(lifetime.is_active)

    def test_monthly_price_updated(self):
        call_command("create_subscription_plans")
        m = SubscriptionPlan.objects.get(slug="monthly-hero")
        self.assertEqual(m.price, Decimal("7.99"))

    def test_yearly_price_updated(self):
        call_command("create_subscription_plans")
        y = SubscriptionPlan.objects.get(slug="yearly-hero")
        self.assertEqual(y.price, Decimal("79.00"))

    def test_idempotent(self):
        call_command("create_subscription_plans")
        call_command("create_subscription_plans")
        self.assertEqual(
            SubscriptionPlan.objects.filter(
                slug__in=["monthly-hero", "yearly-hero"], is_active=True
            ).count(),
            2,
        )
