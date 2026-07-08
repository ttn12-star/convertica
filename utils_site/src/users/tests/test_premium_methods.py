from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from src.users.models import SubscriptionPlan, User


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


class GetHeroesTests(TestCase):
    """The heroes wall (get_heroes / get_top_subscribers) must show every
    currently-active opted-in premium user, INCLUDING lifetime buyers
    (subscription_end_date is NULL), and must exclude expired/refunded users.
    """

    def setUp(self):
        cache.clear()
        self.monthly = SubscriptionPlan.objects.create(
            name="M",
            slug="m-hero",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )
        self.lifetime = SubscriptionPlan.objects.create(
            name="L",
            slug="l-hero",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
        )

    def _hero(self, email, plan, end, opt_in=True):
        u = User.objects.create_user(email=email, password="x")
        u.activate_premium(
            plan=plan,
            period_start=timezone.now(),
            period_end=end,
            provider="lemonsqueezy",
            provider_subscription_id="s_" + email,
            provider_customer_id="c_" + email,
        )
        u.display_as_hero = opt_in
        u.save()
        return u

    def _hero_emails(self):
        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")
        return [h.email for h in User.get_heroes()]

    def test_annual_opted_in_appears(self):
        self._hero("a@t.test", self.monthly, timezone.now() + timedelta(days=365))
        self.assertIn("a@t.test", self._hero_emails())

    def test_lifetime_opted_in_appears(self):
        # Regression: lifetime buyers have subscription_end_date=None and were
        # wrongly excluded by the old subscription_end_date__isnull=False filter.
        self._hero("lt@t.test", self.lifetime, None)
        emails = self._hero_emails()
        self.assertIn("lt@t.test", emails)
        self.assertIn("lt@t.test", [u.email for u in User.get_top_subscribers(10)])

    def test_not_opted_in_hidden(self):
        self._hero(
            "no@t.test",
            self.monthly,
            timezone.now() + timedelta(days=365),
            opt_in=False,
        )
        self.assertNotIn("no@t.test", self._hero_emails())

    def test_refunded_hidden(self):
        u = self._hero("ref@t.test", self.monthly, timezone.now() + timedelta(days=365))
        u.deactivate_premium(reason="refunded")
        self.assertNotIn("ref@t.test", self._hero_emails())

    def test_expired_hidden(self):
        self._hero("exp@t.test", self.monthly, timezone.now() - timedelta(days=1))
        self.assertNotIn("exp@t.test", self._hero_emails())
