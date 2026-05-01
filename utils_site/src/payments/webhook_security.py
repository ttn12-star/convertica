"""HMAC signature verification for webhooks."""

import hashlib
import hmac


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
