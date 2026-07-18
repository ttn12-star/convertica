"""The Turnstile widget is rendered off the `captcha_required` context var.

A premium user is exempt from CAPTCHA *verification* (spam_protection), but the
render decision must be exempt too — otherwise the widget stays visible for a
paying user whenever the sticky session flag is set (mobile Referer stripping,
origin gate, honeypot false-positives). Lock premium out of the render path.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from src.frontend.context_processors import turnstile_site_key
from src.users.models import SubscriptionPlan, User


@override_settings(DEBUG=False)  # DEBUG short-circuits the flag to False
class TurnstileContextPremiumTests(TestCase):
    def setUp(self):
        cache.clear()
        self.rf = RequestFactory()
        self.user = User.objects.create_user(email="ctx@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Ctx",
            slug="monthly-ctx",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def _req_with_flag(self, user):
        req = self.rf.get("/pdf-to-word/")
        req.session = {"captcha_required": True}
        req.user = user
        return req

    def test_free_user_still_sees_captcha_flag(self):
        ctx = turnstile_site_key(self._req_with_flag(self.user))
        self.assertTrue(ctx["captcha_required"])

    def test_premium_user_captcha_flag_is_suppressed(self):
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_ctx",
            provider_customer_id="cust_ctx",
        )
        ctx = turnstile_site_key(self._req_with_flag(self.user))
        self.assertFalse(ctx["captcha_required"])
