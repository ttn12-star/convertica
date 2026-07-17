"""Premium users must be able to get and use an API key regardless of HOW
they became premium.

Regression for the funnel hole where admin-granted, lifetime, and legacy
premium users (no UserSubscription row → subscription_plan is None) were
locked out of the API-keys dashboard AND rejected by APIKeyAuthentication,
even though they are fully premium everywhere else on the site.
"""

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed
from src.api.auth.api_key_auth import APIKeyAuthentication
from src.users.models import APIKey, SubscriptionPlan, User, UserSubscription


@override_settings(RATELIMIT_ENABLE=False)
class PremiumApiQuotaTest(TestCase):
    def setUp(self):
        # is_subscription_active() caches status per user id; SQLite reuses ids
        # across rolled-back tests, so a stale entry leaks a bogus premium
        # status into fresh users. Clear it for deterministic assertions.
        cache.clear()

    def _admin_premium_user(self, email):
        # Exactly the admin "make premium" path: is_premium flag, no plan,
        # no UserSubscription, no end date.
        u = User.objects.create_user(email=email, password="p")
        u.is_premium = True
        u.subscription_end_date = None
        u.save(update_fields=["is_premium", "subscription_end_date"])
        return u

    def test_non_premium_has_zero_quota(self):
        u = User.objects.create_user(email="free@x.com", password="p")
        self.assertEqual(u.api_quota_per_month, 0)

    def test_admin_granted_premium_gets_fallback_quota(self):
        u = self._admin_premium_user("admin-premium@x.com")
        self.assertEqual(u.api_quota_per_month, User.PREMIUM_API_QUOTA_FALLBACK)
        self.assertGreater(u.api_quota_per_month, 0)

    def test_subscriber_gets_plan_quota(self):
        u = User.objects.create_user(email="sub@x.com", password="p")
        plan = SubscriptionPlan.objects.create(
            name="Y",
            slug="yearly-hero",
            price=79,
            duration_days=365,
            api_quota_per_month=10000,
        )
        u.activate_subscription(plan)
        UserSubscription.objects.create(user=u, plan=plan, status="active")
        self.assertEqual(u.api_quota_per_month, 10000)

    def test_admin_premium_can_open_dashboard_and_create_key(self):
        u = self._admin_premium_user("dash@x.com")
        self.client.force_login(u)
        r = self.client.get(reverse("users:api_keys"))
        self.assertNotContains(r, "Subscribe to unlock", status_code=200)
        r2 = self.client.post(reverse("users:api_key_create"), {"name": "mcp"})
        self.assertEqual(r2.status_code, 302)
        self.assertTrue(APIKey.objects.filter(user=u, name="mcp").exists())

    def test_admin_premium_key_authenticates(self):
        u = self._admin_premium_user("auth@x.com")
        _key, plaintext = APIKey.issue(user=u, name="mcp", scope=["*"])
        req = RequestFactory().post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {plaintext}"
        )
        user, _auth = APIKeyAuthentication().authenticate(req)
        self.assertEqual(user, u)

    def test_expired_premium_still_blocked(self):
        u = User.objects.create_user(email="expired@x.com", password="p")
        u.is_premium = False
        u.save(update_fields=["is_premium"])
        _key, plaintext = APIKey.issue(user=u, name="x", scope=["*"])
        req = RequestFactory().post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {plaintext}"
        )
        with self.assertRaises(AuthenticationFailed):
            APIKeyAuthentication().authenticate(req)
