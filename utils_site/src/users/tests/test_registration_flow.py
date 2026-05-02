"""End-to-end registration + email-verification flow tests.

Exercises the project's two complementary signup paths:

* `/accounts/signup/` — django-allauth's built-in signup view (used for
  social/auth integrations & the canonical email-confirmation pipeline).
* `/<lang>/users/login/` — the project's custom login view (LoginForm)
  which enforces verified email before granting a session.

The flow under test:

    signup → unverified user exists
           → cannot login (verify-first wall)
           → confirm via allauth's HMAC link
           → login succeeds and lands on /users/profile/

These are not unit tests — they hit the real URLconf, real allauth signup
adapter, and real custom login view.
"""

from __future__ import annotations

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from src.users.models import User

# Disable mandatory verification overrides at the test level only where needed.
# Project default is ACCOUNT_EMAIL_VERIFICATION="mandatory"; we keep it that way
# so the verify-first wall is exercised faithfully.


class RegistrationFlowTests(TestCase):
    """Signup → unverified → cannot-login → verify → login → profile."""

    SIGNUP_URL = "/accounts/signup/"

    def setUp(self):
        self.client = Client()
        self.email = "newuser@convertica.test"
        self.password = "Sup3rStr0ngPass!42"

    # ------------------------------------------------------------------
    # 1. Signup creates an unverified user.
    # ------------------------------------------------------------------
    def test_signup_creates_unverified_user(self):
        response = self.client.post(
            self.SIGNUP_URL,
            data={
                "email": self.email,
                "password1": self.password,
                "password2": self.password,
            },
        )
        # allauth redirects on success (302) to verification-sent page.
        # Some configs render a 200 page; both are acceptable.
        self.assertIn(response.status_code, (200, 302))

        # User row exists.
        self.assertTrue(User.objects.filter(email=self.email).exists())
        user = User.objects.get(email=self.email)

        # Email row exists but is NOT verified.
        self.assertTrue(
            EmailAddress.objects.filter(user=user, email=self.email).exists(),
            "allauth must create EmailAddress on signup",
        )
        self.assertFalse(
            EmailAddress.objects.filter(
                user=user, email=self.email, verified=True
            ).exists(),
            "freshly registered user must not be verified",
        )

    # ------------------------------------------------------------------
    # 2. Unverified user cannot log in via the custom login view.
    # ------------------------------------------------------------------
    def test_unverified_user_cannot_login(self):
        # Create user + unverified EmailAddress directly (bypass form
        # to keep the test focused on the verify-first gate).
        user = User.objects.create_user(email=self.email, password=self.password)
        EmailAddress.objects.create(
            user=user, email=self.email, primary=True, verified=False
        )

        login_url = reverse("users:login")
        response = self.client.post(
            login_url,
            data={"email": self.email, "password": self.password},
        )
        # Custom view re-renders login.html with an error context — 200, NOT 302.
        self.assertEqual(response.status_code, 200)
        # Error message comes from src.users.views.user_login.
        # Match liberally — "verify your email" survives translation.
        body = response.content.decode("utf-8", errors="replace").lower()
        self.assertIn("verify your email", body)

    # ------------------------------------------------------------------
    # 3. Email verification flow via allauth confirm link.
    # ------------------------------------------------------------------
    def test_email_verification_flow(self):
        user = User.objects.create_user(email=self.email, password=self.password)
        email_address = EmailAddress.objects.create(
            user=user, email=self.email, primary=True, verified=False
        )

        # Build the HMAC confirmation key (no DB row needed).
        confirmation = EmailConfirmationHMAC(email_address)
        key = confirmation.key

        confirm_url = reverse("account_confirm_email", args=[key])

        # POST to confirm — GET only confirms when ACCOUNT_CONFIRM_EMAIL_ON_GET
        # is True (project default is False). POST is the canonical path.
        response = self.client.post(confirm_url)
        self.assertIn(response.status_code, (200, 302))

        email_address.refresh_from_db()
        self.assertTrue(
            email_address.verified,
            "POST to /accounts/confirm-email/<key>/ must mark email verified",
        )

        # Now login should succeed.
        login_url = reverse("users:login")
        # Logout in case ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION auto-logged-in.
        self.client.logout()
        response = self.client.post(
            login_url,
            data={"email": self.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------------
    # 4. Verified user → login redirects to /users/profile/.
    # ------------------------------------------------------------------
    def test_login_redirects_to_profile(self):
        user = User.objects.create_user(email=self.email, password=self.password)
        EmailAddress.objects.create(
            user=user, email=self.email, primary=True, verified=True
        )

        login_url = reverse("users:login")
        response = self.client.post(
            login_url,
            data={"email": self.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        # Redirect target must be the profile page (i18n-prefixed).
        profile_url = reverse("users:profile")
        self.assertEqual(response.url, profile_url)


@override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
class SignupFormValidationTests(TestCase):
    """Smoke-check that the allauth signup endpoint actually validates input.

    Without this, a regression that allows e.g. mismatched passwords would
    silently let the verification flow proceed with a bogus user.
    """

    SIGNUP_URL = "/accounts/signup/"

    def test_signup_rejects_password_mismatch(self):
        response = self.client.post(
            self.SIGNUP_URL,
            data={
                "email": "mismatch@convertica.test",
                "password1": "Sup3rStr0ngPass!42",
                "password2": "DifferentPass!99",
            },
        )
        # On invalid input allauth re-renders the form (200) — not a redirect.
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="mismatch@convertica.test").exists())
