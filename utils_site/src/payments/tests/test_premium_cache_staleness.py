"""A cached "not premium" answer must not survive an activation."""

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from src.users.models import SubscriptionPlan, User


class StalePremiumCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="cached", email="cached@example.com", password="x"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly-cache",
            price="7.99",
            currency="USD",
            duration_days=30,
        )

    def test_activation_wins_over_a_freshly_cached_negative(self):
        """The exact production sequence: browse, then pay.

        Checking premium anywhere on the site caches the answer for five
        minutes. If the payment webhook lands inside that window, save() used
        to recompute is_premium from the cached "False" and drop the premium a
        customer had just paid for -- while the subscription row and the dates
        all looked correct, so nothing surfaced as an error.
        """
        # Browsing the site caches "not premium" for this user.
        self.assertFalse(self.user.is_subscription_active())

        # The webhook lands moments later.
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="polar",
            provider_subscription_id="sub_cache",
            provider_customer_id="cus_cache",
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium, "paid customer left without premium")
        self.assertTrue(self.user.is_subscription_active())
        self.assertTrue(self.user.is_premium_active)

    def test_expired_end_date_still_clears_premium(self):
        # The other direction must keep working: a past end date means no premium.
        self.user.is_premium = True
        self.user.subscription_start_date = timezone.now() - timedelta(days=60)
        self.user.subscription_end_date = timezone.now() - timedelta(days=1)
        self.user.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
