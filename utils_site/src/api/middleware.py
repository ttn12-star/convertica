"""
API middleware for rate limiting and performance monitoring.
"""

import time

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

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

        # Get client IP
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")

        # Rate limit key
        rate_limit_key = f"rate_limit:{ip}"

        try:
            # Get current count
            current_count = cache.get(rate_limit_key, 0)

            # Check limit (100 requests per minute)
            if current_count >= 100:
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                    },
                    status=429,
                )

            # Increment counter
            cache.set(rate_limit_key, current_count + 1, 60)  # 60 seconds TTL
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


class OperationRunTrackingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            if request.method != "POST":
                return None
            if not request.path.startswith("/api/"):
                return None

            # Exclude non-user operational webhooks to avoid noisy analytics.
            if request.path.startswith("/api/payments/webhook/"):
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
        except Exception:
            pass

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
        except Exception:
            pass
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
                )
            else:
                mark_success(
                    request_id=str(request_id),
                    output_size=None,
                    duration_ms=duration_ms,
                )
        except Exception:
            pass

        return response


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


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers including Content Security Policy (CSP).

    CSP helps prevent XSS attacks by specifying allowed sources for scripts,
    styles, images, and other resources.
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

        # Build CSP policy
        csp_directives = [
            # Default: only same origin
            "default-src 'self'",
            # Scripts: self, inline (for Django templates), Stripe, Turnstile, Google Analytics, Yandex Metrika
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://js.stripe.com "
            "https://challenges.cloudflare.com "
            "https://www.googletagmanager.com "
            "https://www.google-analytics.com "
            "https://mc.yandex.ru "
            "https://accounts.google.com "
            "https://connect.facebook.net",
            # Styles: self, inline (for Tailwind and dynamic styles)
            "style-src 'self' 'unsafe-inline' " "https://fonts.googleapis.com",
            # Fonts: self, Google Fonts
            "font-src 'self' " "https://fonts.gstatic.com " "data:",
            # Images: self, data URIs, blob, common CDNs, Yandex Metrika
            "img-src 'self' data: blob: "
            "https://*.stripe.com "
            "https://www.googletagmanager.com "
            "https://www.google-analytics.com "
            "https://*.google.com "
            "https://*.facebook.com "
            "https://mc.yandex.ru",
            # Connect: self, Stripe, Turnstile, WebSocket, analytics, Yandex Metrika
            "connect-src 'self' "
            "https://api.stripe.com "
            "https://challenges.cloudflare.com "
            "https://www.google-analytics.com "
            "https://mc.yandex.ru "
            "https://accounts.google.com "
            "wss://*.convertica.net "
            "ws://localhost:* "
            "wss://localhost:*",
            # Frames: Stripe checkout, Turnstile, OAuth
            "frame-src 'self' "
            "https://js.stripe.com "
            "https://hooks.stripe.com "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com "
            "https://www.facebook.com",
            # Form actions: self only
            "form-action 'self' "
            "https://accounts.google.com "
            "https://www.facebook.com",
            # Base URI: self only (prevents base tag injection)
            "base-uri 'self'",
            # Object sources: none (prevents Flash/plugins)
            "object-src 'none'",
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
                'payment=(self "https://js.stripe.com"), '
                "usb=()"
            )

        return response

    def _is_debug(self):
        """Check if Django is in debug mode."""
        try:
            from django.conf import settings

            return getattr(settings, "DEBUG", False)
        except Exception:
            return False
