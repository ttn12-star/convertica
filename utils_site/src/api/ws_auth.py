"""Auth helper for WebSocket progress channels.

Kept separate from consumers.py so the (pure) token check is importable and
testable without the optional `channels` dependency.
"""

from urllib.parse import parse_qs

from .task_tokens import verify_task_token


def ws_token_ok(scope, resource_id: str) -> bool:
    """Whether the WS connection carries a valid signed token for resource_id.

    Progress channels broadcast download_url / filename / file_size, so a bare
    task_id (a UUID) must not be enough to subscribe. The client appends
    ``?task_token=<signed>`` (the same token minted on the async POST); we verify
    it against the connection's user (anon -> None) before joining the group.
    """
    qs = parse_qs(scope.get("query_string", b"").decode())
    token = (qs.get("task_token") or [None])[0]
    user = scope.get("user")
    user_id = user.id if user and getattr(user, "is_authenticated", False) else None
    return verify_task_token(token or "", resource_id, user_id=user_id)
