"""Short-lived JWT for authenticating browser API calls.

The web JS calls /api/v1/auth/web-token once per session (Turnstile-gated),
caches the JWT in memory, and attaches it to every /api/v1/<tool>/ call.
The token is HS256-signed with SECRET_KEY, carries scope (which tools it
unlocks) and an IP-fingerprint (so a stolen token can't be used from
another IP).
"""

import hashlib
import time
from typing import Optional

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

WEB_TOKEN_TTL_SECONDS = 15 * 60  # 15 minutes


def _ip_hash(ip: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()[:16]


def mint_web_token(
    scope: list[str], ip: str, ttl_seconds: int = WEB_TOKEN_TTL_SECONDS
) -> str:
    """Issue a signed JWT for the browser to attach to /api/v1 calls.

    scope: list of tool slugs (e.g. ["pdf-to-word"]) or ["*"] for any.
    ip: client IP — gets hashed into the token, verified on use.
    ttl_seconds: negative for already-expired (for tests).
    """
    now = int(time.time())
    payload = {
        "sub": "web",
        "scope": scope,
        "iph": _ip_hash(ip),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


class WebTokenAuthentication(BaseAuthentication):
    """DRF auth class for browser-issued JWTs."""

    keyword = "Bearer"
    prefix = "eyJ"  # JWT base64 starts with this; distinguish from cvk_live_* keys

    def authenticate(self, request) -> tuple | None:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None  # not our auth scheme; defer to next class
        token = header.removeprefix(f"{self.keyword} ")
        if not token.startswith(self.prefix):
            return None  # API key, not a web token; let APIKeyAuth handle it
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Web token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid web token: {e}")

        # Verify IP fingerprint matches caller — stops token theft from
        # different IPs. (CF passes real IP via HTTP_CF_CONNECTING_IP.)
        caller_ip = (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[-1].strip()
            or request.META.get("REMOTE_ADDR", "")
        )
        if payload.get("iph") != _ip_hash(caller_ip):
            raise AuthenticationFailed("Web token bound to different IP")

        # Web tokens are anonymous; user=None, but we expose the parsed
        # payload as request.auth for permission classes to read.
        return (None, payload)
