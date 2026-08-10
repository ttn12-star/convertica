"""HMAC signature verification for webhooks."""

import hashlib
import hmac
import time

# Paddle signatures older than this are rejected: a valid signature stays valid
# forever otherwise, so a captured delivery could be replayed at any point.
# Paddle retries for days, but each retry is re-signed with a fresh timestamp.
PADDLE_MAX_SIGNATURE_AGE = 5 * 60


def verify_lemonsqueezy_signature(body: bytes, signature_hex: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature provided by Lemon Squeezy.

    LS sends the signature in the `X-Signature` header.

    Returns False on any verification failure (empty inputs, wrong digest,
    different lengths). Uses hmac.compare_digest to guard against timing
    attacks.
    """
    if not body or not signature_hex or not secret:
        return False
    try:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    except Exception:
        return False
    return hmac.compare_digest(expected, signature_hex)


def _parse_paddle_signature(header: str) -> tuple[str, str]:
    """Split a `ts=<unix>;h1=<hex>` header into (ts, h1). ('', '') if malformed."""
    ts = h1 = ""
    for part in header.split(";"):
        key, _, value = part.partition("=")
        key = key.strip()
        if key == "ts":
            ts = value.strip()
        elif key == "h1":
            h1 = value.strip()
    return ts, h1


def verify_paddle_signature(
    body: bytes,
    signature_header: str,
    secret: str,
    *,
    max_age: int = PADDLE_MAX_SIGNATURE_AGE,
    now: float | None = None,
) -> bool:
    """Verify the `Paddle-Signature` header.

    Paddle sends `Paddle-Signature: ts=1671552777;h1=<hex>` and signs the
    string `<ts>:<raw body>` with HMAC-SHA256 — note the timestamp is part of
    the signed payload, so it cannot be tampered with independently.

    Rejects anything malformed, mis-signed, or older than `max_age` seconds.
    Timestamps from the future are rejected too: a forged one would otherwise
    push the expiry arbitrarily far out.
    """
    if not body or not signature_header or not secret:
        return False

    ts, h1 = _parse_paddle_signature(signature_header)
    if not ts or not h1:
        return False

    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False

    current = time.time() if now is None else now
    age = current - ts_int
    if age > max_age or age < -max_age:
        return False

    try:
        signed_payload = ts.encode() + b":" + body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    except Exception:
        return False
    return hmac.compare_digest(expected, h1)
