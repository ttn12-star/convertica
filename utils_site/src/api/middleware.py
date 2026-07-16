"""
API middleware for rate limiting and performance monitoring.
"""

import base64
import logging
import os
import time
from datetime import UTC, datetime

from django.http import HttpResponse, JsonResponse
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

op_tracking_logger = logging.getLogger("src.api.operation_run_tracking")


class APIKeyQuotaRefundMiddleware(MiddlewareMixin):
    """Refund the API-key quota unit charged at authentication on failure.

    APIKeyAuthentication charges one quota unit per authenticated request
    (race-safe). Without a refund, a request that ends non-2xx (validation
    400, oversize 413, rate-limit 429, server 500) still burns a paid monthly
    unit. APIKeyAuthentication marks the request with ``_cvk_api_key_charge``;
    here we refund that unit when the response is non-2xx so customers are only
    billed for conversions that actually ran.
    """

    def process_response(self, request, response):
        key_pk = getattr(request, "_cvk_api_key_charge", None)
        if key_pk is not None and getattr(response, "status_code", 200) >= 400:
            try:
                from django.db.models import F
                from src.users.models import APIKey

                APIKey.objects.filter(pk=key_pk).update(
                    usage_this_month=F("usage_this_month") - 1
                )
            except Exception:
                pass  # best-effort; never break the response on a refund error
        return response


class CSPNonceMiddleware(MiddlewareMixin):
    """
    Middleware to generate a unique nonce for Content Security Policy.

    The nonce is generated per-request and used to allow specific inline scripts
    while blocking all other inline scripts (preventing XSS attacks).
    """

    def process_request(self, request):
        # Generate a cryptographically secure random nonce (16 bytes = 128 bits)
        nonce = base64.b64encode(os.urandom(16)).decode("utf-8")
        request.csp_nonce = nonce
        return None


# Graceful degradation if cache is not available
try:
    from django.core.cache import cache

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for API endpoints.

    Limits requests per IP address to prevent abuse.
    """

    def process_request(self, request):
        # Only apply to API endpoints
        if not request.path.startswith("/api/"):
            return None

        # Skip rate limiting if cache is not available
        if not CACHE_AVAILABLE:
            return None

        # Skip rate limiting for task status polling (safe GET endpoint)
        # These are polled frequently during async conversions
        if "/api/tasks/" in request.path and "/status/" in request.path:
            return None

        # Get client IP — prefer CF-Connecting-IP (set by Cloudflare, not spoofable)
        # before falling back to X-Forwarded-For where the leftmost entry is user-controlled.
        ip = (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[-1].strip()
            or request.META.get("REMOTE_ADDR", "")
        )

        # Rate limit key
        rate_limit_key = f"rate_limit:{ip}"

        try:
            # Atomic count for a fixed 60s window. `cache.add` only seeds the
            # key when absent (starts a window); `cache.incr` is atomic, so
            # concurrent same-IP requests (the norm behind Cloudflare) can't
            # lose increments or keep re-setting the TTL the way the old
            # get-then-set did. incr raises if the key expired mid-call — re-seed.
            cache.add(rate_limit_key, 0, 60)
            try:
                current_count = cache.incr(rate_limit_key)
            except ValueError:
                cache.add(rate_limit_key, 0, 60)
                current_count = cache.incr(rate_limit_key)

            # Check limit (100 requests per minute)
            if current_count > 100:
                # This middleware runs before LocaleMiddleware, so the active
                # locale isn't set yet — resolve the user's language from the
                # request (Accept-Language / cookie) so the 429 is localized.
                lang = translation.get_language_from_request(request)
                with translation.override(lang):
                    payload = {
                        "error": _("Rate limit exceeded"),
                        "message": _("Too many requests. Please try again later."),
                    }
                return JsonResponse(payload, status=429)
        except Exception:
            # If cache fails, allow request (graceful degradation)
            pass

        return None


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor request performance.

    Logs slow requests and adds timing headers.
    """

    def process_request(self, request):
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time
            response["X-Process-Time"] = f"{duration:.3f}"

            # Skip monitoring for health check and other system endpoints
            # These endpoints may be slow due to DB/cache checks, which is expected
            skip_paths = ["/health/", "/robots.txt", "/sitemap.xml"]
            if any(request.path.startswith(path) for path in skip_paths):
                return response

            # Log slow requests
            # For API endpoints (conversions), use higher threshold (3 seconds)
            # For other requests, use 1 second threshold
            threshold = 3.0 if request.path.startswith("/api/") else 1.0
            if duration > threshold:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Slow request: {request.path} took {duration:.3f}s")

        return response


def is_conversion_request(request) -> bool:
    """True for POSTs that represent a user conversion/operation.

    Single source of truth shared by OperationRunTrackingMiddleware (analytics)
    and DailyQuotaMiddleware (free-tier daily cap) so "what counts as an
    operation" can never drift between the two.
    """
    if request.method != "POST":
        return False
    if not request.path.startswith("/api/"):
        return False
    # Non-user operational webhooks.
    if request.path.startswith("/api/payments/webhook/"):
        return False
    # Internal task-control endpoints.
    if request.path in (
        "/api/cancel-task/",
        "/api/operation-abandon/",
        "/api/task-background/",
    ):
        return False
    # Non-conversion v1 endpoints (token issuance, feedback). The v1
    # *conversion* endpoints (…/merge, …/split) are NOT here and stay counted.
    return request.path not in (
        "/api/v1/auth/web-token",
        "/api/v1/feedback/",
    )


class OperationRunTrackingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            if not is_conversion_request(request):
                return None

            view_class = getattr(view_func, "view_class", None)

            from .operation_run_middleware_utils import (
                create_operation_run,
                ensure_request_id,
            )

            ensure_request_id(request)

            conversion_type = None
            if view_class is not None:
                conversion_type = getattr(view_class, "CONVERSION_TYPE", None)

            if not conversion_type:
                match = getattr(request, "resolver_match", None)
                conversion_type = getattr(match, "view_name", None) if match else None

            if not conversion_type:
                conversion_type = request.path

            request._op_run_started_ts = time.time()
            request._op_run_request_id = create_operation_run(
                request=request,
                conversion_type=str(conversion_type),
                status="running",
            )
        except Exception as e:
            op_tracking_logger.warning(
                "OperationRun tracking setup failed for %s: %s: %s",
                request.path,
                type(e).__name__,
                e,
            )

        return None

    def process_exception(self, request, exception):
        try:
            request_id = getattr(request, "_op_run_request_id", None)
            started_ts = getattr(request, "_op_run_started_ts", None)
            if not request_id or not started_ts:
                return None

            from .operation_run_middleware_utils import mark_error

            duration_ms = int((time.time() - started_ts) * 1000)
            mark_error(
                request_id=str(request_id),
                error_type=type(exception).__name__,
                error_message=str(exception)[:2000],
                duration_ms=duration_ms,
            )
        except Exception as e:
            op_tracking_logger.warning(
                "OperationRun exception tracking failed: %s: %s", type(e).__name__, e
            )
        return None

    def process_response(self, request, response):
        try:
            request_id = getattr(request, "_op_run_request_id", None)
            started_ts = getattr(request, "_op_run_started_ts", None)
            if not request_id or not started_ts:
                return response

            duration_ms = int((time.time() - started_ts) * 1000)
            status_code = getattr(response, "status_code", 200)

            from django.utils import timezone

            from .operation_run_middleware_utils import (
                extract_error_message,
                mark_http_error,
                mark_success,
                update_operation_run,
            )

            task_id = None
            try:
                data = getattr(response, "data", None)
                if isinstance(data, dict):
                    task_id = data.get("task_id")
            except Exception:
                pass

            if task_id and status_code in (200, 201, 202):
                update_operation_run(
                    request_id=str(request_id),
                    status="queued",
                    task_id=str(task_id),
                    queued_at=timezone.now(),
                    duration_ms=duration_ms,
                )
                return response

            if status_code and int(status_code) >= 400:
                msg = extract_error_message(response) or f"HTTP {status_code}"
                mark_http_error(
                    request_id=str(request_id),
                    error_message=msg,
                    duration_ms=duration_ms,
                    status_code=int(status_code),
                )
            else:
                mark_success(
                    request_id=str(request_id),
                    output_size=None,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            op_tracking_logger.warning(
                "OperationRun response tracking failed: %s: %s", type(e).__name__, e
            )

        return response


class DailyQuotaMiddleware(MiddlewareMixin):
    """Global free-tier daily conversion cap: anon 10 < registered 40 < premium ∞.

    Runs AFTER OperationRunTrackingMiddleware in MIDDLEWARE so a quota 429 is
    still recorded as a rejected operation in analytics (its process_view has
    already created the OperationRun row by the time we short-circuit).

    Pre-view: reject with 429 + register/upgrade links when the day's bucket is
    exhausted. Post-response: count only 2xx outcomes and expose
    X-Daily-Quota-Limit / X-Daily-Quota-Remaining headers the frontend uses for
    the "N conversions left today" nudge. Fail-open on any cache error.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        from django.conf import settings

        # The shared-IP bucket would make unrelated suite tests 429 each other;
        # quota tests opt back in via DAILY_QUOTA_ENFORCE_IN_TESTS.
        if getattr(settings, "TESTING", False) and not getattr(
            settings, "DAILY_QUOTA_ENFORCE_IN_TESTS", False
        ):
            return None
        try:
            if not is_conversion_request(request):
                return None

            # API-key callers (Authorization: Bearer cvk_…) authenticate at the
            # DRF layer AFTER middleware, so request.user is still anonymous
            # here. They are premium-only with their own monthly quota — don't
            # IP-bucket them. (Web tokens are anonymous browser sessions with a
            # different token format and stay quota'd via IP.)
            if request.META.get("HTTP_AUTHORIZATION", "").startswith("Bearer cvk_"):
                return None

            from .daily_quota import get_quota_state, quota_limit_message
            from .premium_utils import is_premium_active

            user = getattr(request, "user", None)
            if is_premium_active(user):
                return None

            key, limit, used = get_quota_state(request)
            if used < limit:
                # Remember the bucket; process_response counts 2xx outcomes.
                request._daily_quota_key = key
                request._daily_quota_limit = limit
                return None

            is_auth = bool(
                user is not None and getattr(user, "is_authenticated", False)
            )
            body = {
                "error": quota_limit_message(is_auth, limit),
                "quota": {"limit": limit, "used": used},
            }
            if is_auth:
                if getattr(settings, "PAYMENTS_ENABLED", True):
                    body["upgrade_url"] = _reverse_or_none(
                        "frontend:pricing", "/pricing/"
                    )
                    body["upgrade_text"] = _("Upgrade to Premium")
            else:
                body["register_url"] = _reverse_or_none(
                    "users:register", "/users/register/"
                )
                body["register_text"] = _("Create a free account")
                if getattr(settings, "PAYMENTS_ENABLED", True):
                    body["upgrade_url"] = _reverse_or_none(
                        "frontend:pricing", "/pricing/"
                    )
                    body["upgrade_text"] = _("Upgrade to Premium")
            response = JsonResponse(body, status=429)
            response["X-Daily-Quota-Limit"] = str(limit)
            response["X-Daily-Quota-Remaining"] = "0"
            return response
        except Exception as e:
            op_tracking_logger.warning(
                "Daily quota check failed for %s: %s: %s",
                request.path,
                type(e).__name__,
                e,
            )
            return None  # fail open

    def process_response(self, request, response):
        key = getattr(request, "_daily_quota_key", None)
        if not key:
            return response
        try:
            limit = int(getattr(request, "_daily_quota_limit", 0) or 0)
            status_code = int(getattr(response, "status_code", 500) or 500)
            if 200 <= status_code < 300:
                from .daily_quota import consume_quota_unit

                used = consume_quota_unit(key)
                response["X-Daily-Quota-Limit"] = str(limit)
                response["X-Daily-Quota-Remaining"] = str(max(0, limit - used))
        except Exception as e:
            op_tracking_logger.warning(
                "Daily quota count failed: %s: %s", type(e).__name__, e
            )
        return response


def _reverse_or_none(view_name: str, fallback: str) -> str:
    try:
        from django.urls import reverse

        return reverse(view_name)
    except Exception:
        return fallback


class FilterProxyRequestsMiddleware(MiddlewareMixin):
    """
    Middleware to filter out proxy CONNECT requests, invalid hosts, and bot scanners.

    This middleware MUST run BEFORE SecurityMiddleware to prevent DisallowedHost
    errors from proxy tunneling attempts and bot scanners. Without this, these
    attacks cause cascading errors in cache middleware when Django tries to
    generate error pages.

    Common attacks blocked:
    - CONNECT method (HTTP proxy tunneling)
    - Invalid HOST headers (httpbin.org, 0.0.0.0:8000, etc.)
    - RDP scanners (mstshash in headers)
    - Invalid HTTP request lines
    """

    def process_request(self, request):
        from django.conf import settings
        from django.http import HttpResponseBadRequest

        # Filter CONNECT requests (HTTP proxy tunneling)
        if request.method == "CONNECT":
            return HttpResponseBadRequest(b"", content_type="text/plain")

        # Get HOST header directly (don't call request.get_host() as it may raise)
        # Check HTTP_HOST first, then SERVER_NAME (used by Django test client)
        host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")

        # Reject empty host (malformed requests from production only)
        # In tests, SERVER_NAME might be empty but that's OK
        if not host:
            return HttpResponseBadRequest(b"", content_type="text/plain")

        # Reject hosts with suspicious characters (binary data, control chars)
        # Valid hostnames only contain alphanumeric, dots, hyphens, colons (for port)
        try:
            host.encode("ascii")
        except UnicodeEncodeError:
            return HttpResponseBadRequest(b"", content_type="text/plain")

        # Strip port from host for validation
        host_without_port = host.split(":")[0].lower()

        # Get allowed hosts from settings
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])

        # If ALLOWED_HOSTS is empty or contains '*', skip validation
        # (development mode)
        if not allowed_hosts or "*" in allowed_hosts:
            return None

        # Allow Django test client (uses 'testserver' as default host)
        if host_without_port == "testserver":
            return None

        # Check if host is valid
        is_valid_host = False
        for allowed in allowed_hosts:
            allowed_lower = allowed.lower()
            # Handle wildcard subdomains (e.g., .convertica.net)
            if allowed_lower.startswith("."):
                if host_without_port == allowed_lower[1:] or host_without_port.endswith(
                    allowed_lower
                ):
                    is_valid_host = True
                    break
            elif host_without_port == allowed_lower:
                is_valid_host = True
                break

        if not is_valid_host:
            # Return 400 silently without logging - these are just bot scanners
            # The response is minimal to avoid giving attackers information
            return HttpResponseBadRequest(b"", content_type="text/plain")

        return None


# Date we cut legacy /api/* off: until then requests get warning headers, after
# they get 410.
# WARNING: the site frontend itself still POSTs to /api/<tool>/ (window.API_URL),
# NOT /api/v1/*. The 2026-07-01 value fired and 410'd every converter in prod
# (~14h outage). Keep this far in the future until the frontend is migrated off
# legacy paths; do NOT re-arm without migrating window.API_URL first.
LEGACY_API_SUNSET = datetime(2099, 1, 1, tzinfo=UTC)


class LegacyAPIDeprecationMiddleware(MiddlewareMixin):
    """Add Deprecation/Sunset headers on /api/<tool>/ legacy paths.

    After LEGACY_API_SUNSET, return 410 Gone instead of proxying to the
    view. Tool-polling endpoints (/api/tasks/) and /api/docs/ are NOT
    affected — those stay alive.
    """

    def __call__(self, request):
        path = request.path
        # Match /api/<tool>/ but NOT /api/v1/<tool>/, /api/tasks/<id>/...,
        # /api/docs/, /api/docs.json, or other non-tool admin paths
        is_legacy_tool = (
            path.startswith("/api/")
            and not path.startswith("/api/v1/")
            and not path.startswith("/api/tasks/")
            and not path.startswith("/api/docs")
        )
        if is_legacy_tool:
            now = datetime.now(UTC)
            if now > LEGACY_API_SUNSET:
                return HttpResponse(
                    "Legacy /api/* removed. Use /api/v1/* with API key "
                    "auth — see https://convertica.net/api/docs/",
                    status=410,
                    content_type="text/plain",
                )
        response = self.get_response(request)
        if is_legacy_tool:
            response["Deprecation"] = "true"
            response["Sunset"] = LEGACY_API_SUNSET.strftime("%a, %d %b %Y %H:%M:%S GMT")
            response["Link"] = '</api/docs/>; rel="successor-version"'
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers including Content Security Policy (CSP).

    CSP helps prevent XSS attacks by specifying allowed sources for scripts,
    styles, images, and other resources.

    Uses nonce-based CSP for inline scripts to prevent XSS while allowing
    legitimate inline scripts in our templates.
    """

    def process_response(self, request, response):
        # Skip CSP for admin panel (it has its own inline scripts)
        if request.path.startswith("/admin"):
            return response

        # Skip CSP for API responses (JSON doesn't need CSP)
        if request.path.startswith("/api/"):
            return response

        # Skip CSP for Swagger docs
        if request.path.startswith("/swagger") or request.path.startswith("/redoc"):
            return response

        # Get nonce from request (set by CSPNonceMiddleware)
        nonce = getattr(request, "csp_nonce", "")

        # Build CSP policy
        # Note: nonce is generated but not used in CSP because 'strict-dynamic'
        # was removed - it disables 'unsafe-inline' for inline event handlers
        _ = nonce  # Silence unused variable warning, nonce is still set on request

        csp_directives = [
            # Default: only same origin
            "default-src 'self'",
            # Scripts: self + unsafe-inline + unsafe-eval for inline scripts and analytics
            # Note: 'strict-dynamic' was removed because it disables 'unsafe-inline'
            # for inline event handlers (onclick, onload, etc.)
            # 'unsafe-eval' is required by Google Tag Manager for dynamic code execution
            # Host allowlist for trusted third-party scripts
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://app.lemonsqueezy.com "
            "https://assets.lemonsqueezy.com "
            "https://challenges.cloudflare.com "
            "https://www.googletagmanager.com "
            "https://www.google-analytics.com "
            "https://ssl.google-analytics.com "
            "https://tagmanager.google.com "
            "https://accounts.google.com "
            "https://connect.facebook.net "
            "https://pagead2.googlesyndication.com "
            "https://partner.googleadservices.com "
            "https://cdnjs.cloudflare.com",
            # Styles: self, inline (for Tailwind and dynamic styles)
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            # Fonts: self, Google Fonts
            "font-src 'self' https://fonts.gstatic.com data:",
            # Images: self, data URIs, blob, common CDNs, YouTube thumbnails
            "img-src 'self' data: blob: "
            "https://*.lemonsqueezy.com "
            "https://www.googletagmanager.com "
            "https://www.google-analytics.com "
            "https://*.google.com "
            "https://*.facebook.com "
            "https://i.ytimg.com "
            "https://img.youtube.com "
            # Backlink directory badges (footer "Featured on" row)
            "https://findly.tools "
            "https://img.turbo0.com "
            "https://smollaunch.com "
            "https://pagead2.googlesyndication.com "
            "https://googleads.g.doubleclick.net "
            "https://tpc.googlesyndication.com",
            # Connect: self, Lemon Squeezy, Turnstile, WebSocket, analytics
            "connect-src 'self' "
            "https://api.lemonsqueezy.com "
            "https://*.lemonsqueezy.com "
            "https://challenges.cloudflare.com "
            "https://www.google-analytics.com "
            "https://*.google-analytics.com "
            "https://www.googletagmanager.com "
            "https://region1.google-analytics.com "
            "https://accounts.google.com "
            "wss://*.convertica.net "
            "ws://localhost:* "
            "wss://localhost:*",
            # Frames: Lemon Squeezy checkout, Turnstile, OAuth, YouTube, AdSense
            "frame-src 'self' "
            "https://app.lemonsqueezy.com "
            "https://*.lemonsqueezy.com "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com "
            "https://www.facebook.com "
            "https://www.youtube-nocookie.com "
            "https://www.youtube.com "
            "https://googleads.g.doubleclick.net "
            "https://tpc.googlesyndication.com",
            # Form actions: self only
            "form-action 'self' https://accounts.google.com https://www.facebook.com",
            # Base URI: self only (prevents base tag injection)
            "base-uri 'self'",
            # Object sources: none (prevents Flash/plugins)
            "object-src 'none'",
            # Workers: self + blob (pdf.js instantiates its worker from a blob URL
            # for the Sign PDF / page-count preview; without this it falls back to
            # a main-thread fake worker and logs a CSP violation).
            "worker-src 'self' blob:",
            # Upgrade insecure requests in production
            "upgrade-insecure-requests" if not self._is_debug() else "",
        ]

        # Filter out empty directives and join
        csp_policy = "; ".join(d for d in csp_directives if d)

        # Add CSP header
        response["Content-Security-Policy"] = csp_policy

        # Add other security headers (complement to Django's built-in ones)
        # Referrer Policy - don't leak full URL to external sites
        if "Referrer-Policy" not in response:
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - disable unnecessary browser features
        if "Permissions-Policy" not in response:
            response["Permissions-Policy"] = (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                'payment=(self "https://app.lemonsqueezy.com"), '
                "usb=()"
            )

        if "X-Robots-Tag" not in response:
            if getattr(response, "status_code", 200) >= 400:
                response["X-Robots-Tag"] = "noindex, nofollow"
            else:
                content_type = response.get("Content-Type", "")
                if content_type.startswith("text/html"):
                    from src.frontend.seo import get_request_seo_context

                    robots_meta = get_request_seo_context(request)["robots_meta"]
                    if robots_meta.startswith("noindex"):
                        response["X-Robots-Tag"] = robots_meta

        return response

    def _is_debug(self):
        """Check if Django is in debug mode."""
        try:
            from django.conf import settings

            return getattr(settings, "DEBUG", False)
        except Exception:
            return False
