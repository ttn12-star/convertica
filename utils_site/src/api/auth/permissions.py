"""DRF permission classes for /api/v1."""

from rest_framework.permissions import BasePermission


class IsAuthenticatedOrWebToken(BasePermission):
    """Allow if request authenticated via API key (user set) OR via web token.

    Reject raw anonymous calls. The web JS gets a token via /api/v1/auth/web-token
    (Turnstile-gated) and attaches Authorization: Bearer <jwt>; API users
    attach their cvk_live_<...> key. Either is OK.
    """

    message = "API key or web token required. See /api/docs/."

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        # WebTokenAuth sets request.auth to the JWT payload dict.
        auth = request.auth
        if not (isinstance(auth, dict) and auth.get("sub") == "web"):
            return False

        # Scope enforcement is OPT-IN: only views that declare a
        # ``web_token_scope`` slug are checked against the token's scope list
        # ("*" always passes). Without this a token minted for one tool could
        # be replayed against another (anonymous, IP-bound — no privilege
        # escalation, hence opt-in rather than a blanket gate that could 403
        # real users on any tool-slug/format mismatch).
        required = getattr(view, "web_token_scope", None)
        if not required:
            return True
        scope = auth.get("scope") or []
        return "*" in scope or required in scope
