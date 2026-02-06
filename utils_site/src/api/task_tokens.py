"""
Task token helpers for securing task control endpoints.
"""

from django.conf import settings
from django.core import signing

TOKEN_TTL_SECONDS = int(getattr(settings, "TASK_TOKEN_TTL", 3600) or 3600)
_SIGNING_SALT = "convertica.task-token"


def _build_payload(task_id: str, user_id: int | None) -> str:
    user_part = "" if user_id is None else str(user_id)
    return f"{task_id}:{user_part}"


def create_task_token(task_id: str, user_id: int | None = None) -> str:
    """Create a signed task token for the given task/user pair."""
    signer = signing.TimestampSigner(salt=_SIGNING_SALT)
    payload = _build_payload(task_id, user_id)
    return signer.sign(payload)


def verify_task_token(
    task_token: str, task_id: str, user_id: int | None = None
) -> bool:
    """Verify a task token matches the expected task/user pair."""
    if not task_token or not task_id:
        return False
    signer = signing.TimestampSigner(salt=_SIGNING_SALT)
    expected = _build_payload(task_id, user_id)
    try:
        value = signer.unsign(task_token, max_age=TOKEN_TTL_SECONDS)
    except signing.BadSignature:
        return False
    return value == expected
