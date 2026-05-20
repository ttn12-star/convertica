from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

_LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


@override_settings(RATELIMIT_ENABLE=True, CACHES=_LOCMEM_CACHES)
class AnonRateLimitTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_anon_31st_post_blocked(self):
        client = APIClient()
        for i in range(30):
            r = client.post("/api/jpg-to-pdf/", {})  # 400 expected (no file)
            self.assertIn(r.status_code, (400, 415))
        r = client.post("/api/jpg-to-pdf/", {})
        self.assertEqual(r.status_code, 429, "31st anon hit should be rate-limited")


@override_settings(RATELIMIT_ENABLE=True, CACHES=_LOCMEM_CACHES)
class NoDoubleCountTest(TestCase):
    """Regression for spec-review finding: dispatch+post decorators stacked,
    halving the effective limit for subclasses that call super().post().
    """

    def setUp(self):
        cache.clear()

    def test_subclass_calling_super_does_not_double_count(self):
        # pdf-to-word is a subclass that DOES call super().post() — if the
        # decorators were stacked, this test would fail at iteration 15.
        # Patch validate_spam_protection so rapid-fire test requests are not
        # blocked by the 2-second minimum-time-between-requests spam check;
        # that is orthogonal to what we are testing here.
        client = APIClient()
        with patch(
            "src.api.base_views.validate_spam_protection",
            return_value=None,
        ):
            for i in range(30):
                r = client.post("/api/pdf-to-word/", {})
                self.assertIn(
                    r.status_code,
                    (400, 415, 405),
                    f"iteration {i}: got {r.status_code} — should not be 429 yet",
                )
            r = client.post("/api/pdf-to-word/", {})
        self.assertEqual(r.status_code, 429, "31st hit should be limited (not earlier)")
