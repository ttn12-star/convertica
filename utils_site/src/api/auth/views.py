"""Endpoints under /api/v1/auth/."""

import logging

from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from src.api.rate_limit_utils import handle_rate_limit_exception
from src.api.spam_protection import verify_turnstile

from .web_token import WEB_TOKEN_TTL_SECONDS, mint_web_token

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key="ip", rate="20/m", method="POST", block=False)
@ratelimit(key="ip", rate="200/h", method="POST", block=False)
def web_token_view(request):
    """Issue a 15-min JWT, gated by Turnstile.

    Per-IP rate limited before Turnstile verification — a burst loop
    can't drain the Turnstile quota or pin workers. Legit flow mints ~1
    token per ~14 min per tab, so 20/m + 200/h is plenty of headroom.
    """
    if getattr(request, "limited", False):
        return handle_rate_limit_exception(request, Ratelimited("ip"))

    body = request.data or {}
    ts_token = body.get("turnstile_token")
    if not ts_token:
        return Response({"error": "turnstile_token required"}, status=400)

    caller_ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[-1].strip()
        or request.META.get("REMOTE_ADDR", "")
    )
    if not verify_turnstile(ts_token, caller_ip):
        return Response({"error": "captcha verification failed"}, status=403)

    scope = body.get("scope") or ["*"]
    if not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
        return Response({"error": "scope must be list of strings"}, status=400)

    token = mint_web_token(scope=scope, ip=caller_ip)
    return Response({"token": token, "expires_in": WEB_TOKEN_TTL_SECONDS})
