"""Signed, short-lived tokens proving a real successful operation.

A token is minted when an OperationRun reaches ``success`` and handed to the
browser via the ``X-Convertica-Feedback-Token`` response header. It is the
anti-abuse mechanism for the feedback endpoint: unforgeable and time-limited,
it resolves back to the originating operation without exposing internal IDs.
"""

from django.core import signing

_SIGNING_SALT = "convertica.feedback-token"
FEEDBACK_TOKEN_TTL = 24 * 60 * 60  # 24 hours


def create_feedback_token(
    *, request_id: str | None = None, task_id: str | None = None
) -> str:
    """Sign a token resolving to a successful OperationRun.

    Use ``request_id`` for sync operations, ``task_id`` for async operations.
    """
    signer = signing.TimestampSigner(salt=_SIGNING_SALT)
    if request_id:
        payload = f"r:{request_id}"
    elif task_id:
        payload = f"t:{task_id}"
    else:
        raise ValueError("request_id or task_id is required")
    return signer.sign(payload)


def resolve_feedback_token(token: str) -> tuple[str, str] | None:
    """Return ``(kind, value)`` where kind is 'r' or 't', else None.

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
    if kind not in ("r", "t") or not value:
        return None
    return kind, value
