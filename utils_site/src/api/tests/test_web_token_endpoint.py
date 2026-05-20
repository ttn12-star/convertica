from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    TURNSTILE_SECRET_KEY="test-secret",
    DEBUG=False,
    # Tests share the Redis ratelimit cache; disable so the new per-IP cap
    # on web_token_view doesn't leak across cases and 403 the test client.
    RATELIMIT_ENABLE=False,
)
class WebTokenEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("src.api.auth.views.verify_turnstile", return_value=True)
    def test_valid_turnstile_returns_token(self, _):
        r = self.client.post(
            "/api/v1/auth/web-token",
            {"turnstile_token": "ok-token", "scope": ["pdf-to-word"]},
            format="json",
            HTTP_REFERER="https://convertica.net/en/pdf-to-word/",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.json())
        self.assertEqual(r.json()["expires_in"], 900)

    @patch("src.api.auth.views.verify_turnstile", return_value=False)
    def test_failed_turnstile_returns_403(self, _):
        r = self.client.post(
            "/api/v1/auth/web-token",
            {"turnstile_token": "bad", "scope": ["pdf-to-word"]},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_missing_turnstile_returns_400(self):
        r = self.client.post("/api/v1/auth/web-token", {}, format="json")
        self.assertEqual(r.status_code, 400)


@override_settings(
    TURNSTILE_SECRET_KEY="test-secret",
    DEBUG=False,
    RATELIMIT_ENABLE=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class WebTokenRateLimitTest(TestCase):
    """The mint endpoint must rate-limit per IP so a burst loop can't drain
    Turnstile quota or pin workers. Legit flow needs ~1 mint per 14 min."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = APIClient()

    def test_21st_mint_in_a_minute_blocked(self):
        # 20/m cap → 21st request from the same IP gets blocked.
        for _ in range(20):
            r = self.client.post("/api/v1/auth/web-token", {}, format="json")
            # 400 turnstile_token required is the expected response while
            # under cap (rate-limit doesn't kick in yet).
            self.assertIn(r.status_code, (400, 403))
        r = self.client.post("/api/v1/auth/web-token", {}, format="json")
        self.assertEqual(
            r.status_code, 429, "21st mint within a minute must be rate-limited"
        )
