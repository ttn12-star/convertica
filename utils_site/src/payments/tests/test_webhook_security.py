import hashlib
import hmac

from django.test import TestCase
from src.payments.webhook_security import verify_lemonsqueezy_signature


def _sig(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


class VerifyLemonSqueezySignatureTests(TestCase):
    SECRET = b"shh-secret-32chars-or-more-secret"

    def test_accepts_correct_signature(self):
        body = b'{"event":"x"}'
        sig = _sig(self.SECRET, body)
        self.assertTrue(verify_lemonsqueezy_signature(body, sig, self.SECRET.decode()))

    def test_rejects_wrong_signature(self):
        body = b'{"event":"x"}'
        self.assertFalse(
            verify_lemonsqueezy_signature(body, "deadbeef", self.SECRET.decode())
        )

    def test_rejects_empty_signature_header(self):
        self.assertFalse(verify_lemonsqueezy_signature(b"x", "", "secret"))

    def test_rejects_empty_secret(self):
        self.assertFalse(verify_lemonsqueezy_signature(b"x", "anything", ""))

    def test_constant_time_compare(self):
        # Different-length signature should not raise; should return False.
        body = b"x"
        self.assertFalse(verify_lemonsqueezy_signature(body, "short", "secret"))
