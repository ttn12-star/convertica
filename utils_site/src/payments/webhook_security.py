"""HMAC signature verification for webhooks."""

import base64
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


# Polar signs with the Standard Webhooks scheme, which mandates the same
# five-minute replay window Paddle uses.
POLAR_MAX_SIGNATURE_AGE = 5 * 60


def _polar_key(secret: str) -> bytes:
    """Derive the HMAC key from a Polar webhook secret: it is the raw bytes.

    Standard Webhooks on its own treats the secret as base64 and decodes it,
    but Polar base64-ENCODES the secret before handing it to that library:

        const base64Secret = Buffer.from(secret, "utf-8").toString("base64");
        const webhook = new Webhook(base64Secret);
            -- polarsource/polar-js, src/webhooks.ts

    The two transforms cancel, so the key is simply the secret's UTF-8 bytes,
    and there is no `whsec_` prefix to strip. Decoding the secret as base64
    here instead produced a different key and rejected every real delivery
    with a 400 -- verified against live production deliveries on 2026-08-28.
    """
    return secret.encode("utf-8")


def verify_polar_signature(
    body: bytes,
    headers,
    secret: str,
    *,
    max_age: int = POLAR_MAX_SIGNATURE_AGE,
    now: float | None = None,
) -> bool:
    """Verify Standard Webhooks headers as sent by Polar.

    Polar sends `webhook-id`, `webhook-timestamp` (unix seconds) and
    `webhook-signature` (a space-separated list of `v1,<base64>` entries, so a
    secret can be rotated without dropping deliveries). The signed string is
    `<id>.<timestamp>.<raw body>`, meaning neither the id nor the timestamp can
    be tampered with independently.

    Rejects anything malformed, mis-signed, or outside the replay window.
    """
    if not body or not secret:
        return False

    msg_id = headers.get("webhook-id") or ""
    msg_ts = headers.get("webhook-timestamp") or ""
    msg_sig = headers.get("webhook-signature") or ""
    if not msg_id or not msg_ts or not msg_sig:
        return False

    try:
        ts_float = float(msg_ts)
    except (TypeError, ValueError):
        return False

    current = time.time() if now is None else now
    age = current - ts_float
    if age > max_age or age < -max_age:
        return False

    try:
        key = _polar_key(secret)
        if not key:
            return False
        to_sign = f"{msg_id}.{msg_ts}.".encode() + body
        expected = hmac.new(key, to_sign, hashlib.sha256).digest()
    except Exception:
        return False

    for entry in msg_sig.split(" "):
        version, _, candidate = entry.partition(",")
        if version != "v1" or not candidate:
            continue
        try:
            given = base64.b64decode(candidate)
        except Exception:
            continue
        if hmac.compare_digest(expected, given):
            return True
    return False
