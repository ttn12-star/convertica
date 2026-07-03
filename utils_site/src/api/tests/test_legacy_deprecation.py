from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(RATELIMIT_ENABLE=False)
class LegacyAPIDeprecationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_legacy_tool_carries_deprecation_headers(self):
        # any legacy /api/<tool>/ that exists should pick up the headers
        r = self.client.get(
            "/api/pdf-to-word/"
        )  # likely 405 (POST-only), but headers attach pre-response
        self.assertEqual(r.get("Deprecation"), "true")
        self.assertIn("Sunset", r.headers)
        self.assertIn('rel="successor-version"', r.headers.get("Link", ""))

    def test_v1_does_not_carry_deprecation_headers(self):
        r = self.client.get("/api/v1/pdf-to-word/")
        self.assertIsNone(r.get("Deprecation"))

    def test_tasks_polling_not_deprecated(self):
        # /api/tasks/<id>/status/ is the polling endpoint — never deprecated
        r = self.client.get("/api/tasks/abc-123/status/")
        # The path won't resolve to a valid task — could be 404 or whatever,
        # but no Deprecation header
        self.assertIsNone(r.get("Deprecation"))

    def test_docs_not_deprecated(self):
        r = self.client.get("/api/docs/")
        self.assertIsNone(r.get("Deprecation"))

    @patch(
        "src.api.middleware.LEGACY_API_SUNSET", datetime(2020, 1, 1, tzinfo=UTC)
    )  # in the past
    def test_legacy_returns_410_after_sunset(self):
        r = self.client.post("/api/pdf-to-word/", {})
        self.assertEqual(r.status_code, 410)
