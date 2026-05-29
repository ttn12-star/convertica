"""Tests for the shared trusted client-IP helper.

Security (CONVERTICA review, 2026-05-29): spam_protection.py read the
*leftmost* X-Forwarded-For entry, which is fully attacker-controlled — a
client sending ``X-Forwarded-For: <random>, <real>`` got a fresh rate-limit /
honeypot / CAPTCHA bucket on every request, defeating all per-IP throttling on
the conversion endpoints. Cloudflare sets the real client IP in
``CF-Connecting-IP`` and appends the trusted hop to the *rightmost* XFF entry,
so those are the values we must trust.
"""

from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase
from src.api.client_ip import get_client_ip


class GetClientIPTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_prefers_cf_connecting_ip(self):
        request = self.rf.get("/", HTTP_CF_CONNECTING_IP="203.0.113.7")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 5.6.7.8"
        self.assertEqual(get_client_ip(request), "203.0.113.7")

    def test_ignores_spoofed_leftmost_xff_uses_rightmost(self):
        # Attacker prepends a fake IP; the trusted proxy hop is rightmost.
        request = self.rf.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "6.6.6.6, 198.51.100.9"
        self.assertEqual(get_client_ip(request), "198.51.100.9")

    def test_single_xff_entry(self):
        request = self.rf.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "198.51.100.9"
        self.assertEqual(get_client_ip(request), "198.51.100.9")

    def test_falls_back_to_remote_addr(self):
        request = self.rf.get("/", REMOTE_ADDR="192.0.2.55")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META.pop("HTTP_CF_CONNECTING_IP", None)
        self.assertEqual(get_client_ip(request), "192.0.2.55")
