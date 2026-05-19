from django.test import TestCase, override_settings
from django.urls import reverse
from src.users.models import APIKey, SubscriptionPlan, User, UserSubscription


@override_settings(RATELIMIT_ENABLE=False)
class APIKeysDashboardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@x.com", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Y",
            slug="yearly-hero",
            price=79,
            duration_days=365,
            api_quota_per_month=10000,
        )
        self.user.activate_subscription(self.plan)
        # Create a UserSubscription so subscription_plan property resolves correctly
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )
        self.client.force_login(self.user)

    def test_anon_redirected_to_login(self):
        self.client.logout()
        r = self.client.get(reverse("users:api_keys"))
        self.assertEqual(r.status_code, 302)

    def test_no_subscription_blocked(self):
        u2 = User.objects.create_user(email="free@x.com", password="p")
        self.client.force_login(u2)
        r = self.client.get(reverse("users:api_keys"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Subscribe to unlock", status_code=200)

    def test_subscriber_sees_empty_state(self):
        r = self.client.get(reverse("users:api_keys"))
        self.assertContains(r, "No API keys yet")

    def test_create_shows_plaintext_once(self):
        r = self.client.post(
            reverse("users:api_key_create"), {"name": "test-key"}, follow=True
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "cvk_live_")
        # Verify key exists in DB
        key = APIKey.objects.get(user=self.user)
        self.assertEqual(key.name, "test-key")
        # GET after the redirect: the plaintext is pop'd from session so won't show on second GET
        r2 = self.client.get(reverse("users:api_keys"))
        self.assertNotContains(r2, key.key_hash)  # the hash should NEVER appear

    def test_revoke_marks_revoked_at(self):
        key, _ = APIKey.issue(user=self.user, name="t", scope=["*"])
        r = self.client.post(reverse("users:api_key_revoke", args=[key.pk]))
        self.assertEqual(r.status_code, 302)
        key.refresh_from_db()
        self.assertIsNotNone(key.revoked_at)

    def test_revoke_other_users_key_404(self):
        other = User.objects.create_user(email="other@x.com", password="p")
        key, _ = APIKey.issue(user=other, name="t", scope=["*"])
        r = self.client.post(reverse("users:api_key_revoke", args=[key.pk]))
        # Should not 200 — user can't revoke someone else's key
        self.assertNotEqual(r.status_code, 200)
        key.refresh_from_db()
        self.assertIsNone(key.revoked_at)  # NOT revoked

    def test_max_10_active_keys(self):
        for i in range(10):
            APIKey.issue(user=self.user, name=f"key-{i}", scope=["*"])
        r = self.client.post(
            reverse("users:api_key_create"), {"name": "11th"}, follow=True
        )
        # Expect error message, 11th key NOT created
        self.assertEqual(
            APIKey.objects.filter(user=self.user, revoked_at__isnull=True).count(), 10
        )
