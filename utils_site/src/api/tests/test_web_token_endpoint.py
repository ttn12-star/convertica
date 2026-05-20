from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(TURNSTILE_SECRET_KEY="test-secret", DEBUG=False)
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
