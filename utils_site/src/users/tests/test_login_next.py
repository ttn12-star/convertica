"""`?next=` handling on the custom login view.

The Workbench CTA sends anonymous users to
`/en/users/login/?next=/en/workbench/`; the view has to bring them back —
without turning into an open redirect.
"""

from __future__ import annotations

from allauth.account.models import EmailAddress
from django.test import TestCase, override_settings
from django.urls import reverse
from src.users.models import User


@override_settings(RATELIMIT_ENABLE=False)
class LoginNextTests(TestCase):
    email = "next-user@convertica.test"
    password = "Sup3rStr0ngPass!42"

    def setUp(self):
        self.user = User.objects.create_user(email=self.email, password=self.password)
        EmailAddress.objects.create(
            user=self.user, email=self.email, primary=True, verified=True
        )
        self.login_url = reverse("users:login")
        self.profile_url = reverse("users:profile")

    def test_post_honours_local_next(self):
        response = self.client.post(
            self.login_url,
            data={
                "email": self.email,
                "password": self.password,
                "next": "/en/workbench/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/en/workbench/")

    def test_post_rejects_offsite_next(self):
        response = self.client.post(
            self.login_url,
            data={
                "email": self.email,
                "password": self.password,
                "next": "https://evil.example/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)

    def test_authenticated_get_honours_next(self):
        self.client.force_login(self.user)
        response = self.client.get(self.login_url, {"next": "/en/workbench/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/en/workbench/")

    def test_authenticated_get_rejects_offsite_next(self):
        self.client.force_login(self.user)
        response = self.client.get(self.login_url, {"next": "https://evil.example/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)

    def test_post_rejects_bare_name_next(self):
        # `redirect()` would try to reverse "profile" and raise NoReverseMatch.
        response = self.client.post(
            self.login_url,
            data={
                "email": self.email,
                "password": self.password,
                "next": "profile",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)

    def test_post_rejects_scheme_relative_next(self):
        response = self.client.post(
            self.login_url,
            data={
                "email": self.email,
                "password": self.password,
                "next": "//evil.example/x",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)

    def test_authenticated_get_rejects_bare_name_next(self):
        self.client.force_login(self.user)
        response = self.client.get(self.login_url, {"next": "profile"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)


@override_settings(
    RATELIMIT_ENABLE=False,
    TURNSTILE_SITE_KEY="",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class RegisterNextTests(TestCase):
    """Sign-up has to carry `next` over to the login page it hands off to."""

    def setUp(self):
        self.url = reverse("users:register")
        self.login_url = reverse("users:login")
        self.data = {
            "email": "next-signup@convertica.test",
            "username": "nextsignup",
            "password1": "Sup3rStr0ngPass!42",
            "password2": "Sup3rStr0ngPass!42",
            "agree_terms": "on",
        }

    def test_register_carries_local_next_to_login(self):
        response = self.client.post(
            self.url, data={**self.data, "next": "/en/workbench/"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.login_url}?next=%2Fen%2Fworkbench%2F")

    def test_register_drops_offsite_next(self):
        response = self.client.post(
            self.url, data={**self.data, "next": "https://evil.example/"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

    def test_register_page_carries_next_into_the_form(self):
        body = self.client.get(self.url, {"next": "/en/workbench/"}).content.decode()
        self.assertIn('name="next" value="/en/workbench/"', body)
