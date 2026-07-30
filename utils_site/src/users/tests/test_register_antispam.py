"""Anti-spam gate and stale-email recycling on the custom /users/register/ view.

Bot signups cost us outbound confirmation mail (bounces on our sending domain)
and squat real email addresses, which blocks the owner from registering until
the 30-day cleanup task removes the row. Both paths are guarded here.
"""

from __future__ import annotations

from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.test import TestCase, override_settings
from django.urls import reverse
from src.users.models import User

PASSWORD = "Sup3rStr0ngPass!42"


@override_settings(
    RATELIMIT_ENABLE=False,
    TURNSTILE_SITE_KEY="test-site-key",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class RegisterAntiSpamTests(TestCase):
    def setUp(self):
        self.url = reverse("users:register")
        self.data = {
            "email": "human@convertica.test",
            "username": "human",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "agree_terms": "on",
        }

    @override_settings(DEBUG=False)
    def test_page_renders_the_widget_it_demands(self):
        # With a site key configured the POST gate requires a token, so the page
        # must actually render the widget — otherwise signup is a dead end.
        body = self.client.get(self.url).content.decode()
        self.assertIn("cf-turnstile", body)
        self.assertIn('name="website"', body)

    def test_filled_honeypot_creates_no_account(self):
        response = self.client.post(
            self.url, data={**self.data, "website": "spam.example"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email=self.data["email"]).exists())

    @patch("src.api.spam_protection.verify_turnstile", return_value=False)
    def test_missing_captcha_creates_no_account(self, _mock):
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email=self.data["email"]).exists())

    @patch("src.api.spam_protection.verify_turnstile", return_value=True)
    def test_valid_signup_creates_unverified_account(self, _mock):
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email=self.data["email"])
        self.assertFalse(
            EmailAddress.objects.filter(user=user, verified=True).exists(),
            "a fresh signup must not be verified",
        )

    @patch("src.api.spam_protection.verify_turnstile", return_value=True)
    def test_unverified_squatter_is_recycled(self, _mock):
        squatter = User.objects.create_user(
            email=self.data["email"], username="bot9134", password=PASSWORD
        )
        EmailAddress.objects.create(
            user=squatter, email=self.data["email"], primary=True, verified=False
        )

        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=squatter.pk).exists())
        self.assertEqual(User.objects.get(email=self.data["email"]).username, "human")

    @patch("src.api.spam_protection.verify_turnstile", return_value=True)
    def test_verified_account_is_not_recycled(self, _mock):
        owner = User.objects.create_user(
            email=self.data["email"], username="owner", password=PASSWORD
        )
        EmailAddress.objects.create(
            user=owner, email=self.data["email"], primary=True, verified=True
        )

        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=owner.pk).exists())
        self.assertEqual(User.objects.filter(email=self.data["email"]).count(), 1)

    @patch("src.api.spam_protection.verify_turnstile", return_value=True)
    def test_social_account_without_verified_email_is_not_recycled(self, _mock):
        from allauth.socialaccount.models import SocialAccount

        google_user = User.objects.create_user(
            email=self.data["email"], username="gsocial", password=PASSWORD
        )
        SocialAccount.objects.create(user=google_user, provider="google", uid="42")

        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=google_user.pk).exists())
