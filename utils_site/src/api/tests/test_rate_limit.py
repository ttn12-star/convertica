from django.test import TestCase, override_settings
from rest_framework.test import APIClient

_LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


@override_settings(RATELIMIT_ENABLE=True, CACHES=_LOCMEM_CACHES)
class AnonRateLimitTest(TestCase):
    def test_anon_31st_post_blocked(self):
        client = APIClient()
        for i in range(30):
            r = client.post("/api/jpg-to-pdf/", {})  # 400 expected (no file)
            self.assertIn(r.status_code, (400, 415))
        r = client.post("/api/jpg-to-pdf/", {})
        self.assertEqual(r.status_code, 429, "31st anon hit should be rate-limited")
