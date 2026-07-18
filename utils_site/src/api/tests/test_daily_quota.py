"""Global daily quota engine + middleware contract.

The end-to-end within-limit/over-limit/429-CTA flows are covered in
test_convert_heic.py (a real conversion endpoint). Here: the engine's
identity/limit/key semantics and the middleware invariants that would
silently break monetization if regressed — successes-only counting,
premium exemption, and the TESTING opt-out.
"""

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from src.api.daily_quota import (
    _cache_key,
    _identity_and_limit,
    consume_quota_unit,
    get_quota_state,
)
from src.api.middleware import is_conversion_request
from src.users.models import User

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM, DAILY_QUOTA_ANON=10, DAILY_QUOTA_REGISTERED=40)
class DailyQuotaEngineTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_anonymous_identity_is_ip_with_anon_limit(self):
        request = self.factory.post("/api/x/", REMOTE_ADDR="10.1.2.3")
        request.user = None
        identity, limit = _identity_and_limit(request)
        self.assertEqual(identity, "ip:10.1.2.3")
        self.assertEqual(limit, 10)

    def test_authenticated_identity_is_pk_with_registered_limit(self):
        user = User.objects.create_user(email="dq@t.test", password="passw0rd!")
        request = self.factory.post("/api/x/")
        request.user = user
        identity, limit = _identity_and_limit(request)
        self.assertEqual(identity, f"u:{user.pk}")
        self.assertEqual(limit, 40)

    def test_cache_key_is_calendar_day_scoped(self):
        """The date in the key IS the reset mechanism — tomorrow = new bucket."""
        key = _cache_key("ip:10.1.2.3")
        self.assertEqual(
            key, f"daily_quota:ip:10.1.2.3:{timezone.now().date().isoformat()}"
        )

    def test_consume_and_state_roundtrip(self):
        request = self.factory.post("/api/x/", REMOTE_ADDR="10.9.9.9")
        request.user = None
        key, limit, used = get_quota_state(request)
        self.assertEqual(used, 0)
        self.assertEqual(consume_quota_unit(key), 1)
        self.assertEqual(consume_quota_unit(key), 2)
        _key, _limit, used = get_quota_state(request)
        self.assertEqual(used, 2)

    def test_is_conversion_request_classification(self):
        post = lambda path: self.factory.post(path)  # noqa: E731
        self.assertTrue(is_conversion_request(post("/api/merge-pdf/")))
        self.assertTrue(is_conversion_request(post("/api/pdf-to-word/async/")))
        self.assertFalse(is_conversion_request(self.factory.get("/api/merge-pdf/")))
        self.assertFalse(is_conversion_request(post("/frontend-page/")))
        self.assertFalse(is_conversion_request(post("/api/payments/webhook/ls/")))
        self.assertFalse(is_conversion_request(post("/api/cancel-task/")))
        self.assertFalse(is_conversion_request(post("/api/v1/auth/web-token")))


@override_settings(
    CACHES=LOCMEM,
    RATELIMIT_ENABLE=False,
    DAILY_QUOTA_ANON=2,
    DAILY_QUOTA_ENFORCE_IN_TESTS=True,
)
class DailyQuotaMiddlewareTests(TestCase):
    """Middleware invariants via a real endpoint (cheap 400 path)."""

    URL = "/api/image/heic-convert/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    def _bad_post(self):
        """Invalid upload -> 400 from the serializer, cheap and deterministic."""
        bad = SimpleUploadedFile("x.heic", b"not a heic", content_type="image/heic")
        return self.client.post(
            self.URL,
            data={"image_file": bad, "output_format": "JPEG"},
            format="multipart",
        )

    def test_rejected_request_does_not_consume_quota(self):
        response = self._bad_post()
        self.assertGreaterEqual(response.status_code, 400)
        key = f"daily_quota:ip:127.0.0.1:{timezone.now().date().isoformat()}"
        self.assertIsNone(cache.get(key))

    @override_settings(DAILY_QUOTA_ENFORCE_IN_TESTS=False)
    def test_middleware_is_inert_in_tests_without_optin(self):
        """Without the opt-in flag the shared-IP bucket must never fill up
        (unrelated suite tests would otherwise 429 each other)."""
        # Pre-fill the bucket over the limit; requests must still get through
        # to the view (here: to its 400 validation, not a 429).
        key = f"daily_quota:ip:127.0.0.1:{timezone.now().date().isoformat()}"
        cache.set(key, 99, 3600)
        response = self._bad_post()
        self.assertNotEqual(response.status_code, 429)

    def test_over_limit_blocked_before_view_runs(self):
        key = f"daily_quota:ip:127.0.0.1:{timezone.now().date().isoformat()}"
        cache.set(key, 2, 3600)  # DAILY_QUOTA_ANON=2 already used
        response = self._bad_post()
        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertIn("register_url", body)
        self.assertEqual(response["X-Daily-Quota-Remaining"], "0")

    def test_forged_non_live_bearer_does_not_bypass_quota(self):
        """Regression: a bogus `Bearer cvk_<x>` (not the real cvk_live_
        namespace) must NOT skip the daily quota. Before the fix it did, and
        because APIKeyAuthentication ignores non-cvk_live_ tokens the request
        then ran as anonymous — unlimited un-metered conversions."""
        key = f"daily_quota:ip:127.0.0.1:{timezone.now().date().isoformat()}"
        cache.set(key, 2, 3600)  # DAILY_QUOTA_ANON=2 already used
        bad = SimpleUploadedFile("x.heic", b"not a heic", content_type="image/heic")
        response = self.client.post(
            self.URL,
            data={"image_file": bad, "output_format": "JPEG"},
            format="multipart",
            HTTP_AUTHORIZATION="Bearer cvk_forged_token_value",
        )
        self.assertEqual(response.status_code, 429)

    def test_live_namespace_bearer_bypasses_quota_but_bogus_key_401s(self):
        """The real cvk_live_ namespace is let through the IP quota here
        (metered separately at the DRF layer); a bogus live key therefore
        reaches DRF auth and is rejected 401 — never a free conversion."""
        key = f"daily_quota:ip:127.0.0.1:{timezone.now().date().isoformat()}"
        cache.set(key, 2, 3600)
        bad = SimpleUploadedFile("x.heic", b"not a heic", content_type="image/heic")
        response = self.client.post(
            self.URL,
            data={"image_file": bad, "output_format": "JPEG"},
            format="multipart",
            HTTP_AUTHORIZATION="Bearer cvk_live_bogusprefix_secretxxxxxxxxxxxx",
        )
        # Not 429 (quota was bypassed) and not 2xx/400 (never reached the view):
        # DRF APIKeyAuthentication rejects the unknown key first. DRF returns
        # 403 (not 401) because APIKeyAuthentication defines no
        # authenticate_header(); either way it is a rejection, never a run.
        self.assertEqual(response.status_code, 403)

    def test_premium_user_is_exempt(self):
        from datetime import timedelta

        user = User.objects.create_user(email="dqp@t.test", password="passw0rd!")
        user.is_premium = True
        user.subscription_end_date = timezone.now() + timedelta(days=30)
        user.save()
        cache.delete(f"user_premium_active:{user.pk}")
        # Session login: the middleware must see the premium user (DRF
        # force_authenticate would leave request.user anonymous here).
        self.client.force_login(user)
        key = f"daily_quota:u:{user.pk}:{timezone.now().date().isoformat()}"
        cache.set(key, 99, 3600)  # would block anyone non-premium
        response = self._bad_post()
        self.assertNotEqual(response.status_code, 429)  # exempt: reaches the view
        self.assertNotIn("X-Daily-Quota-Limit", response.headers)
