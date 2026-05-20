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
        # WebTokenAuth sets request.auth to the JWT payload dict
        return isinstance(request.auth, dict) and request.auth.get("sub") == "web"
