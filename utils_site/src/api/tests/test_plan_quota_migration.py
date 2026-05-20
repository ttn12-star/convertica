from django.test import TestCase
from src.users.models import SubscriptionPlan


class PlanQuotaTest(TestCase):
    def test_field_default_is_zero(self):
        # New plans not in the 3-tier defaults get quota 0 (no API access)
        plan = SubscriptionPlan.objects.create(
            name="Test",
            slug="test-tier",
            price=0,
            duration_days=30,
        )
        self.assertEqual(plan.api_quota_per_month, 0)

    def test_field_accepts_value(self):
        plan = SubscriptionPlan.objects.create(
            name="Test",
            slug="test-tier",
            price=0,
            duration_days=30,
            api_quota_per_month=5000,
        )
        self.assertEqual(plan.api_quota_per_month, 5000)
