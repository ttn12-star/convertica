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
