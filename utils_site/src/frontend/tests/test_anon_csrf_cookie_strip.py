"""Anonymous GETs of cacheable pages must not set the csrftoken cookie.

Cloudflare refuses to cache any response carrying Set-Cookie, so the
"Cache anonymous HTML" cache rule only works if tool pages stop setting
csrftoken for anonymous visitors. Login/signup/contact keep the cookie —
those forms are real Django-CSRF form posts for anonymous users.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from src.users.models import User


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class AnonCsrfCookieStripTests(TestCase):
    def test_anonymous_tool_page_sets_no_csrf_cookie(self):
        response = self.client.get("/en/word-to-pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("csrftoken", response.cookies)

    def test_anonymous_login_page_keeps_csrf_cookie(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_authenticated_tool_page_keeps_csrf_cookie(self):
        user = User.objects.create_user(
            username="csrfuser", email="csrf@example.com", password="pass1234"
        )
        # allauth's auth backend rejects plain client.login(); force the session.
        self.client.force_login(user)
        response = self.client.get("/en/word-to-pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
