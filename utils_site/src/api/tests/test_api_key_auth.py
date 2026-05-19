from datetime import timedelta

from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from src.api.auth.api_key_auth import APIKeyAuthentication
from src.users.models import APIKey, SubscriptionPlan, User, UserSubscription


class APIKeyAuthTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="dev@x.com", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Yearly",
            slug="yearly-hero",
            price=79,
            duration_days=365,
            api_quota_per_month=10,  # tiny for tests
        )
        self.user.activate_subscription(self.plan)
        # Create a UserSubscription so subscription_plan property resolves
        # (activate_subscription sets dates on User but does not create a
        # UserSubscription row — that is the payment-provider path).
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
        self.auth = APIKeyAuthentication()

    def _req(self, key):
        return self.factory.post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {key}"
        )

    def test_valid_key_authenticates(self):
        user, auth_obj = self.auth.authenticate(self._req(self.plaintext))
        self.assertEqual(user, self.user)
        self.assertEqual(auth_obj, self.key)

    def test_revoked_key_rejected(self):
        self.key.revoke()
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(self._req(self.plaintext))

    def test_no_active_subscription_rejected(self):
        # Force the subscription to expire by setting end date in the past
        # and clearing the Redis cache so is_subscription_active() re-evaluates.
        self.user.subscription_end_date = timezone.now() - timedelta(days=1)
        self.user.is_premium = False
        self.user._subscription_changed = True
        self.user.save()
        # Explicitly clear the subscription cache so the auth class sees the new state
        cache.delete(f"user_subscription_status_{self.user.id}")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(self._req(self.plaintext))

    def test_quota_increment_and_exhaustion(self):
        # Exhaust the 10-call quota
        for _ in range(10):
            self.auth.authenticate(self._req(self.plaintext))
        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(self._req(self.plaintext))
        self.assertIn("quota", str(ctx.exception.detail).lower())

    def test_unknown_key_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(self._req("cvk_live_xxxxxxxxxxxxbogus"))

    def test_non_bearer_header_returns_none(self):
        # Authentication chain: this class returns None so the next
        # authenticator (WebTokenAuth/Session) can try.
        request = self.factory.post("/api/v1/x/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_web_token_passed_through(self):
        # When the Authorization is a JWT (starts with eyJ), this class
        # returns None to defer to WebTokenAuthentication.
        request = self.factory.post(
            "/api/v1/x/", HTTP_AUTHORIZATION="Bearer eyJabc.def.xyz"
        )
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
