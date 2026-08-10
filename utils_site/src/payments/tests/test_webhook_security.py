import hashlib
import hmac

from django.test import TestCase
from src.payments.webhook_security import (
    PADDLE_MAX_SIGNATURE_AGE,
    verify_lemonsqueezy_signature,
    verify_paddle_signature,
)


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


def _paddle_sig(secret: bytes, body: bytes, ts: int) -> str:
    digest = hmac.new(
        secret, f"{ts}".encode() + b":" + body, hashlib.sha256
    ).hexdigest()
    return f"ts={ts};h1={digest}"


class VerifyPaddleSignatureTests(TestCase):
    SECRET = b"pdl_ntfset_secret"
    NOW = 1_786_000_000.0

    def _check(self, header, *, body=b'{"event_type":"subscription.created"}'):
        return verify_paddle_signature(body, header, self.SECRET.decode(), now=self.NOW)

    def test_accepts_fresh_signature(self):
        body = b'{"event_type":"subscription.created"}'
        self.assertTrue(self._check(_paddle_sig(self.SECRET, body, int(self.NOW))))

    def test_rejects_tampered_body(self):
        # Signature computed over the original body must not validate the
        # payload an attacker actually sends.
        header = _paddle_sig(self.SECRET, b'{"amount":100}', int(self.NOW))
        self.assertFalse(self._check(header, body=b'{"amount":999999}'))

    def test_rejects_replay_beyond_window(self):
        old = int(self.NOW) - PADDLE_MAX_SIGNATURE_AGE - 1
        body = b'{"event_type":"subscription.created"}'
        self.assertTrue(  # same signature was valid when it was fresh
            verify_paddle_signature(
                body, _paddle_sig(self.SECRET, body, old), self.SECRET.decode(), now=old
            )
        )
        self.assertFalse(self._check(_paddle_sig(self.SECRET, body, old)))

    def test_rejects_timestamp_from_the_future(self):
        future = int(self.NOW) + PADDLE_MAX_SIGNATURE_AGE + 1
        body = b'{"event_type":"subscription.created"}'
        self.assertFalse(self._check(_paddle_sig(self.SECRET, body, future)))

    def test_rejects_wrong_secret(self):
        body = b'{"event_type":"subscription.created"}'
        header = _paddle_sig(b"other_secret", body, int(self.NOW))
        self.assertFalse(self._check(header))

    def test_rejects_malformed_headers(self):
        body = b'{"event_type":"subscription.created"}'
        good = _paddle_sig(self.SECRET, body, int(self.NOW))
        digest = good.split("h1=")[1]
        for header in (
            "",
            "garbage",
            f"h1={digest}",  # no timestamp
            f"ts={int(self.NOW)}",  # no digest
            f"ts=not-a-number;h1={digest}",
        ):
            with self.subTest(header=header):
                self.assertFalse(self._check(header))
