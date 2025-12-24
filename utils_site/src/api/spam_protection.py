"""
Anti-spam protection utilities for API endpoints.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from .logging_utils import build_request_context, get_logger

logger = get_logger(__name__)


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """
    Verify Cloudflare Turnstile token.

    Args:
        token: Turnstile response token
        remote_ip: Client IP address (optional)

    Returns:
        True if verification successful, False otherwise
    """
    # Skip CAPTCHA verification in development mode
    if settings.DEBUG:
        logger.debug("CAPTCHA verification skipped (DEBUG mode)")
        return True

    secret = getattr(settings, "TURNSTILE_SECRET_KEY", None)
    if not secret:
        logger.warning("Turnstile not configured, skipping verification")
        return True

    # When Turnstile is configured, an empty token means the user did not
    # complete the challenge, so we must fail verification.
    if not token:
        return False

    try:
        import requests

        data = {
            "secret": secret,
            "response": token,
        }
        if remote_ip:
            data["remoteip"] = remote_ip

        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=data,
            timeout=5,
        )
        response.raise_for_status()
        result = response.json()

        return result.get("success", False)
    except Exception as e:
        # Fail-open to avoid blocking users if Turnstile is down/reachable issues
        logger.warning(
            "Turnstile verification error (allowing request)",
            extra={
                "error": str(e),
                "remote_ip": remote_ip,
                "token_present": bool(token),
                "event": "turnstile_unavailable",
            },
            exc_info=True,
        )
        return True


def check_honeypot(request: HttpRequest, honeypot_field: str = "website") -> bool:
    """
    Check honeypot field - if filled, it's likely a bot.

    Args:
        request: HTTP request
        honeypot_field: Name of the honeypot field

    Returns:
        True if honeypot is empty (good), False if filled (bot detected)
    """
    # Check POST data
    if hasattr(request, "data"):
        honeypot_value = request.data.get(honeypot_field, "")
    else:
        honeypot_value = request.POST.get(honeypot_field, "")

    # If honeypot is filled, it's a bot
    if honeypot_value:
        logger.warning(
            f"Honeypot field '{honeypot_field}' was filled - possible bot",
            extra={
                **build_request_context(request),
                "honeypot_field": honeypot_field,
                "honeypot_value": honeypot_value[:50],  # Log first 50 chars only
            },
        )
        return False

    return True


def check_rate_limit_by_ip(
    request: HttpRequest,
    limit: int = 10,
    window: int = 60,
    key_prefix: str = "spam_protection",
) -> tuple[bool, str | None]:
    """
    Check rate limit by IP address.

    Args:
        request: HTTP request
        limit: Maximum number of requests
        window: Time window in seconds
        key_prefix: Cache key prefix

    Returns:
        Tuple of (is_allowed, error_message)
    """
    # Get client IP
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")

    cache_key = f"{key_prefix}:{ip}"

    try:
        current_count = cache.get(cache_key, 0)

        if current_count >= limit:
            logger.warning(
                f"Rate limit exceeded for IP {ip}",
                extra={
                    **build_request_context(request),
                    "ip": ip,
                    "limit": limit,
                    "window": window,
                },
            )
            return False, f"Too many requests. Please try again in {window} seconds."

        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return True, None
    except Exception as e:
        logger.error(f"Rate limit check error: {str(e)}", exc_info=True)
        # On error, allow request (fail open)
        return True, None


def check_minimum_time_between_requests(
    request: HttpRequest, min_seconds: int = 2, key_prefix: str = "request_timing"
) -> tuple[bool, str | None]:
    """
    Check minimum time between requests (prevents rapid-fire bot requests).

    Args:
        request: HTTP request
        min_seconds: Minimum seconds between requests
        key_prefix: Cache key prefix

    Returns:
        Tuple of (is_allowed, error_message)
    """
    # Get client IP
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")

    cache_key = f"{key_prefix}:{ip}"
    current_time = time.time()

    try:
        last_request_time = cache.get(cache_key)

        if last_request_time:
            time_since_last = current_time - last_request_time
            if time_since_last < min_seconds:
                logger.warning(
                    f"Request too soon after previous request for IP {ip}",
                    extra={
                        **build_request_context(request),
                        "ip": ip,
                        "time_since_last": time_since_last,
                        "min_seconds": min_seconds,
                    },
                )
                return False, f"Please wait {min_seconds} seconds between requests."

        # Update last request time
        cache.set(cache_key, current_time, min_seconds * 2)
        return True, None
    except Exception as e:
        logger.error(f"Timing check error: {str(e)}", exc_info=True)
        return True, None


def validate_spam_protection(request: HttpRequest) -> Response | None:
    """
    Comprehensive spam protection validation.

    Checks:
    1. hCaptcha (if enabled)
    2. Honeypot field
    3. Rate limiting by IP
    4. Minimum time between requests

    Args:
        request: HTTP request

    Returns:
        Response if spam detected, None if OK
    """
    context = build_request_context(request)

    # 1. Check honeypot
    if not check_honeypot(request):
        return Response(
            {"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Check rate limit (stricter for file uploads)
    is_allowed, error_msg = check_rate_limit_by_ip(
        request,
        limit=20,  # 20 requests per minute for file uploads
        window=60,
        key_prefix="file_upload_spam",
    )
    if not is_allowed:
        return Response({"error": error_msg}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # 3. Check minimum time between requests
    is_allowed, error_msg = check_minimum_time_between_requests(
        request, min_seconds=2  # At least 2 seconds between requests
    )
    if not is_allowed:
        return Response({"error": error_msg}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # 4. Check if CAPTCHA is required (after failed attempts)
    captcha_required = request.session.get("captcha_required", False)

    # 5. Verify Turnstile (if required or token provided)
    turnstile_token = None
    if hasattr(request, "data"):
        turnstile_token = request.data.get("turnstile_token", "") or request.data.get(
            "cf-turnstile-response", ""
        )
    else:
        turnstile_token = request.POST.get("turnstile_token", "") or request.POST.get(
            "cf-turnstile-response", ""
        )

    # If CAPTCHA is required but not provided, reject the request
    if captcha_required and not turnstile_token:
        logger.warning(
            "CAPTCHA required but not provided",
            extra={**context, "ip": request.META.get("REMOTE_ADDR")},
        )
        return Response(
            {
                "error": "CAPTCHA verification required. Please complete the CAPTCHA and try again."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if turnstile_token:
        # Get client IP for Turnstile verification
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            remote_ip = x_forwarded_for.split(",")[0].strip()
        else:
            remote_ip = request.META.get("REMOTE_ADDR")

        if not verify_turnstile(turnstile_token, remote_ip):
            logger.warning(
                "Turnstile verification failed", extra={**context, "ip": remote_ip}
            )
            return Response(
                {"error": "CAPTCHA verification failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # CAPTCHA verified successfully - reset failed attempts
            request.session["failed_attempts"] = 0
            request.session["captcha_required"] = False

    return None
