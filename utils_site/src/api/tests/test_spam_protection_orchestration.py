"""Coverage for validate_spam_protection orchestration (CONVERTICA audit gap #3).

The honeypot -> CAPTCHA escalation is the anti-abuse gate for anonymous
conversions and was only exercised indirectly. Lock the key branches.
"""

from __future__ import annotations

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings
from src.api.spam_protection import check_honeypot, validate_spam_protection


class HoneypotTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_empty_honeypot_passes(self):
        self.assertTrue(check_honeypot(self.rf.post("/api/x/", {})))

    def test_filled_honeypot_is_bot(self):
        self.assertFalse(check_honeypot(self.rf.post("/api/x/", {"website": "spam"})))


@override_settings(DEBUG=False)
class ValidateSpamProtectionTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.rf = RequestFactory()

    def test_filled_honeypot_returns_400(self):
        resp = validate_spam_protection(
            self.rf.post("/api/pdf-to-word/", {"website": "bot"}, REMOTE_ADDR="1.2.3.4")
        )
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 400)

    def test_ip_flagged_for_captcha_without_token_returns_400(self):
        # IP previously flagged (e.g. after failed attempts) and no turnstile
        # token provided -> rejected.
        cache.set("captcha_required_ip:5.6.7.8", True, 3600)
        resp = validate_spam_protection(
            self.rf.post("/api/pdf-to-word/", {}, REMOTE_ADDR="5.6.7.8")
        )
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 400)
