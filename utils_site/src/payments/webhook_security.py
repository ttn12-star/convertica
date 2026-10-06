"""HMAC signature verification for webhooks."""

import base64
import hashlib
import hmac
import time

from src.api.logging_utils import get_logger

logger = get_logger(__name__)

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


def _polar_keys(secret: str) -> list[bytes]:
    """HMAC keys a Polar webhook secret can sign with, legacy first.

    Legacy signing (endpoints created before 8 September 2026, ours): the key
    is the secret's raw UTF-8 bytes. Polar base64-ENCODES the secret before
    handing it to Standard Webhooks, which decodes it back:

        const base64Secret = Buffer.from(secret, "utf-8").toString("base64");
        const webhook = new Webhook(base64Secret);
            -- polarsource/polar-js, src/webhooks.ts

    Decoding the secret as base64 instead rejected every real delivery with a
    400 (verified against live deliveries on 2026-08-28).

    Standard Webhooks (endpoints created, or secrets reset, from 8 September
    2026): the key is the base64 payload after the `whsec_` prefix. Resetting
    the secret in the dashboard switches the endpoint to it, so try both, as
    Polar's own SDKs do; otherwise one reset silently 400s every payment.
    """
    keys = [secret.encode("utf-8")]
    try:
        payload = secret.removeprefix("whsec_")
        # Pad as Polar's SDK does: a secret pasted into .env without its
        # trailing "=" must still verify.
        standard = base64.b64decode(payload + "=" * (-len(payload) % 4), validate=True)
    except Exception:
        standard = b""
    if standard and standard not in keys:
        keys.append(standard)
    return keys


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
        return _polar_reject("missing webhook-id/timestamp/signature header", msg_id)

    try:
        ts_float = float(msg_ts)
    except (TypeError, ValueError):
        return _polar_reject("non-numeric webhook-timestamp", msg_id)

    current = time.time() if now is None else now
    age = current - ts_float
    if age > max_age or age < -max_age:
        return _polar_reject(
            f"timestamp outside the replay window ({age:.0f}s)", msg_id
        )

    to_sign = f"{msg_id}.{msg_ts}.".encode() + body
    expected = [
        hmac.new(key, to_sign, hashlib.sha256).digest() for key in _polar_keys(secret)
    ]

    for entry in msg_sig.split(" "):
        version, _, candidate = entry.partition(",")
        if version != "v1" or not candidate:
            continue
        try:
            given = base64.b64decode(candidate)
        except Exception:
            continue
        if any(hmac.compare_digest(e, given) for e in expected):
            return True
    # Usually a different secret: another Polar account (the sandbox) pointed at
    # this URL, or the dashboard secret was reset without updating .env.
    return _polar_reject("signature matches neither secret scheme", msg_id)


def _polar_reject(reason: str, msg_id: str) -> bool:
    logger.warning(
        f"Polar webhook rejected: {reason}",
        extra={
            "event": "polar_signature_rejected",
            "reason": reason,
            "webhook_id": msg_id,
        },
    )
    return False
