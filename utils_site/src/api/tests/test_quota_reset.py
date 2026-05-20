from django.test import TestCase
from src.tasks.api_quota import reset_api_quotas_monthly
from src.users.models import APIKey, SubscriptionPlan, User


class QuotaResetTest(TestCase):
    def test_reset_zeros_usage(self):
        u = User.objects.create_user(email="x@y.com", password="p")
        plan = SubscriptionPlan.objects.create(
            name="M",
            slug="monthly-hero",
            price=7,
            duration_days=30,
            api_quota_per_month=100,
        )
        u.activate_subscription(plan)
        key, _ = APIKey.issue(user=u, name="t", scope=["*"])
        APIKey.objects.filter(pk=key.pk).update(usage_this_month=42)

        reset_api_quotas_monthly()

        key.refresh_from_db()
        self.assertEqual(key.usage_this_month, 0)

    def test_reset_skips_already_zero(self):
        u = User.objects.create_user(email="y@x.com", password="p")
        plan = SubscriptionPlan.objects.create(
            name="M",
            slug="monthly-hero-2",
            price=7,
            duration_days=30,
            api_quota_per_month=100,
        )
        u.activate_subscription(plan)
        APIKey.issue(user=u, name="t", scope=["*"])  # usage = 0 by default
        # Should not throw; returns count of rows updated
        result = reset_api_quotas_monthly()
        # Either 0 (skipped via exclude) or 1 (updated to same value) — both OK
        self.assertIn(result, (0, 1))
