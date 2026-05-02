from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from src.users.models import SubscriptionPlan


class CreateSubscriptionPlansTests(TestCase):
    def test_creates_three_plans(self):
        call_command("create_subscription_plans")
        slugs = set(SubscriptionPlan.objects.values_list("slug", flat=True))
        self.assertIn("monthly-hero", slugs)
        self.assertIn("yearly-hero", slugs)
        self.assertIn("lifetime-hero", slugs)

    def test_lifetime_plan_has_flag(self):
        call_command("create_subscription_plans")
        lifetime = SubscriptionPlan.objects.get(slug="lifetime-hero")
        self.assertTrue(lifetime.is_lifetime)
        self.assertEqual(lifetime.price, Decimal("129.00"))

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
                slug__in=["monthly-hero", "yearly-hero", "lifetime-hero"]
            ).count(),
            3,
        )
