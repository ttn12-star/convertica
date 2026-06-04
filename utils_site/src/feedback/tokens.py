"""Signed, short-lived tokens proving a real successful operation.

A token is minted on a successful conversion response and handed to the browser
via the ``X-Convertica-Feedback-Token`` header. It is the anti-abuse mechanism
for the feedback endpoint: unforgeable and time-limited.

Two flavours, matching the two real conversion paths:

* ``t:<task_id>`` — async conversions. The Celery path records an OperationRun
  keyed by ``task_id``; feedback binds to it (status check + per-operation dedup).
* ``s:<tool_slug>`` — sync conversions. The legacy sync ``post`` path records no
  OperationRun, so the token simply carries the tool slug; the rating is stored
  with ``operation_run=None`` (client-side dedup via sessionStorage).
"""

from django.core import signing

_SIGNING_SALT = "convertica.feedback-token"
FEEDBACK_TOKEN_TTL = 24 * 60 * 60  # 24 hours


def create_feedback_token(
    *, task_id: str | None = None, tool_slug: str | None = None
) -> str:
    """Sign a feedback token.

    Use ``task_id`` for async conversions, ``tool_slug`` for sync conversions.
    """
    signer = signing.TimestampSigner(salt=_SIGNING_SALT)
    if task_id:
        payload = f"t:{task_id}"
    elif tool_slug:
        payload = f"s:{tool_slug}"
    else:
        raise ValueError("task_id or tool_slug is required")
    return signer.sign(payload)


def resolve_feedback_token(token: str) -> tuple[str, str] | None:
    """Return ``(kind, value)`` where kind is 't' (task_id) or 's' (tool_slug).

    None is returned for empty, malformed, tampered, or expired tokens.
    """
    if not token:
        return None
    signer = signing.TimestampSigner(salt=_SIGNING_SALT)
    try:
        payload = signer.unsign(token, max_age=FEEDBACK_TOKEN_TTL)
    except signing.BadSignature:
        return None
    kind, _, value = payload.partition(":")
    if kind not in ("t", "s") or not value:
        return None
    return kind, value
