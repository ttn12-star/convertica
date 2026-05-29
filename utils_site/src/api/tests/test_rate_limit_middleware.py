"""Coverage for RateLimitMiddleware IP-trust + limits (CONVERTICA audit gap #5).

The middleware's security property is which IP it keys on: CF-Connecting-IP
(set by Cloudflare, not spoofable) first, then the RIGHTMOST X-Forwarded-For
entry (the trusted hop) — never the attacker-controlled leftmost. A regression
here lets an attacker dodge the 100/min limit by rotating a fake leftmost XFF.
"""

from __future__ import annotations

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase
from src.api.middleware import RateLimitMiddleware


class RateLimitMiddlewareTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.mw = RateLimitMiddleware(lambda r: None)
        self.rf = RequestFactory()

    def _req(self, **meta):
        r = self.rf.post("/api/pdf-to-word/async/")
        r.META.update(meta)
        return r

    def test_non_api_path_is_not_limited(self):
        r = self.rf.get("/en/")
        self.assertIsNone(self.mw.process_request(r))

    def test_status_polling_is_skipped(self):
        r = self.rf.get("/api/tasks/abc/status/", REMOTE_ADDR="9.9.9.9")
        cache.set("rate_limit:9.9.9.9", 999, 60)
        self.assertIsNone(self.mw.process_request(r))

    def test_keys_on_cf_connecting_ip_not_xff(self):
        # Limit reached for the CF IP -> 429 (proves CF-Connecting-IP is used).
        cache.set("rate_limit:203.0.113.7", 100, 60)
        resp = self.mw.process_request(
            self._req(
                HTTP_CF_CONNECTING_IP="203.0.113.7",
                HTTP_X_FORWARDED_FOR="6.6.6.6, 5.5.5.5",
            )
        )
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 429)

    def test_uses_rightmost_xff_not_spoofable_leftmost(self):
        # No CF header. Limit reached only for the rightmost (trusted) hop.
        cache.set("rate_limit:198.51.100.9", 100, 60)
        resp = self.mw.process_request(
            self._req(HTTP_X_FORWARDED_FOR="6.6.6.6, 198.51.100.9")
        )
        self.assertEqual(resp.status_code, 429)

    def test_spoofed_leftmost_xff_does_not_hit_limit(self):
        # Limit reached for the attacker's faked leftmost value must be ignored.
        cache.set("rate_limit:6.6.6.6", 100, 60)
        resp = self.mw.process_request(
            self._req(HTTP_X_FORWARDED_FOR="6.6.6.6, 198.51.100.9")
        )
        self.assertIsNone(resp)  # not limited — leftmost is not trusted
