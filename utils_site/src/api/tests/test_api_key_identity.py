"""Regression: cvk_live_ API-key requests must carry premium identity into the
pre-view middleware/rate-limit layers, not be treated as anonymous free-tier.

Root cause fixed here: DRF authenticates the key only inside the view, so
RateLimitMiddleware, the dispatch-level combined_rate_limit, OperationRun
analytics and DailyQuota all saw AnonymousUser and applied the 30/h anonymous
conversion rate + "Anonymous/free" attribution. APIKeyIdentityMiddleware +
resolve_api_key_user establish the real user early, without charging quota.
"""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone
from src.api.auth.api_key_auth import resolve_api_key_user
from src.api.middleware import APIKeyIdentityMiddleware
from src.users.models import APIKey, SubscriptionPlan, User, UserSubscription


class APIKeyIdentityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="apidev@x.com", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Yearly",
            slug="yearly-hero",
            price=79,
            duration_days=365,
            api_quota_per_month=1000,
        )
        self.user.activate_subscription(self.plan)
        now = timezone.now()
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=365),
        )
        self.key, self.plaintext = APIKey.issue(user=self.user, name="ci", scope=["*"])
        self.factory = RequestFactory()
        self.mw = APIKeyIdentityMiddleware(lambda r: None)

    def _req(self, auth=None):
        extra = {"HTTP_AUTHORIZATION": auth} if auth else {}
        r = self.factory.post("/api/v1/pdf-to-word/", **extra)
        r.user = AnonymousUser()  # state left by AuthenticationMiddleware
        return r

    # --- resolver establishes identity WITHOUT metering ---
    def test_resolve_returns_user_without_charging(self):
        before = APIKey.objects.get(pk=self.key.pk).usage_this_month
        self.assertEqual(
            resolve_api_key_user(self._req(f"Bearer {self.plaintext}")), self.user
        )
        after = APIKey.objects.get(pk=self.key.pk).usage_this_month
        self.assertEqual(before, after)  # metering stays in DRF auth only

    def test_resolve_none_for_no_key(self):
        self.assertIsNone(resolve_api_key_user(self._req()))

    def test_resolve_none_for_forged_key(self):
        self.assertIsNone(
            resolve_api_key_user(self._req("Bearer cvk_live_" + "0" * 44))
        )

    def test_resolve_none_for_revoked_key(self):
        self.key.revoke()
        self.assertIsNone(resolve_api_key_user(self._req(f"Bearer {self.plaintext}")))

    # --- middleware injects the premium user for the pre-view layers ---
    def test_middleware_sets_user_for_valid_key(self):
        r = self._req(f"Bearer {self.plaintext}")
        self.mw.process_request(r)
        self.assertEqual(r.user, self.user)
        self.assertTrue(r.user.is_authenticated)

    def test_middleware_leaves_anonymous_without_key(self):
        r = self._req()
        self.mw.process_request(r)
        self.assertFalse(r.user.is_authenticated)

    def test_middleware_leaves_anonymous_for_forged_key(self):
        r = self._req("Bearer cvk_live_" + "0" * 44)
        self.mw.process_request(r)
        self.assertFalse(r.user.is_authenticated)
