from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription


class ActivatePremiumTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@t.test", password="x")
        self.monthly = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )
        self.lifetime = SubscriptionPlan.objects.create(
            name="Lifetime",
            slug="lifetime",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
        )

    def test_activates_subscription(self):
        now = timezone.now()
        end = now + timedelta(days=30)
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now,
            period_end=end,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_1",
            provider_customer_id="ls_cust_1",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNotNone(self.user.subscription_end_date)
        self.assertEqual(self.user.payment_provider, "lemonsqueezy")
        self.assertEqual(self.user.provider_customer_id, "ls_cust_1")

    def test_activates_lifetime_with_null_end_date(self):
        self.user.activate_premium(
            plan=self.lifetime,
            period_start=timezone.now(),
            period_end=None,  # lifetime
            provider="lemonsqueezy",
            provider_subscription_id="",
            provider_customer_id="ls_cust_2",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(self.user.subscription_end_date)
        self.assertTrue(self.user.is_subscription_active())

    def test_extends_active_subscription(self):
        now = timezone.now()
        # First activation
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_x",
            provider_customer_id="ls_cust_x",
        )
        original_end = self.user.subscription_end_date

        # Second activation while active — should set new period_end (renewal)
        new_end = now + timedelta(days=60)
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now,
            period_end=new_end,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_x",
            provider_customer_id="ls_cust_x",
        )
        self.user.refresh_from_db()
        self.assertGreater(self.user.subscription_end_date, original_end)


class DeactivatePremiumTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@t.test", password="x")
        self.user.is_premium = True
        self.user.subscription_start_date = timezone.now() - timedelta(days=15)
        self.user.subscription_end_date = timezone.now() + timedelta(days=15)
        self.user.consecutive_subscription_days = 15
        # Skip auto-recalculation so our explicit streak value (15) is preserved
        # instead of being overwritten by _calculate_subscription_days.
        self.user._skip_days_calculation = True
        self.user.save()
        self.user._skip_days_calculation = False

    def test_deactivate_cancelled_resets_streak(self):
        self.user.deactivate_premium(reason="cancelled")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.user.consecutive_subscription_days, 0)

    def test_deactivate_expired_keeps_streak(self):
        self.user.deactivate_premium(reason="expired")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        # streak preserved — user paid in full for the period
        self.assertEqual(self.user.consecutive_subscription_days, 15)

    def test_deactivate_refunded_resets_streak(self):
        self.user.deactivate_premium(reason="refunded")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.user.consecutive_subscription_days, 0)


class ApplyGraceTests(TestCase):
    def test_extends_subscription_end_date(self):
        u = User.objects.create_user(email="g@t.test", password="x")
        u.is_premium = True
        u.subscription_start_date = timezone.now() - timedelta(days=10)
        u.subscription_end_date = timezone.now()  # expired now
        u.save()

        grace_until = timezone.now() + timedelta(days=3)
        u.apply_grace(until=grace_until)
        u.refresh_from_db()
        self.assertEqual(u.subscription_end_date, grace_until)
        self.assertTrue(u.is_premium)
