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

            try:
                from .async_views import AsyncConversionAPIView
            except Exception:
                AsyncConversionAPIView = None

            view_class = getattr(view_func, "view_class", None)
            if (
                AsyncConversionAPIView
                and view_class
                and issubclass(view_class, AsyncConversionAPIView)
            ):
                return None

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
    Middleware to filter out proxy CONNECT requests and other suspicious requests.

    This prevents DisallowedHost errors from proxy tunneling attempts (e.g., CONNECT ipinfo.io:443).
    These requests are typically from bots/scanners trying to use the server as a proxy.
    """

    def process_request(self, request):
        # Filter CONNECT requests (HTTP proxy tunneling)
        if request.method == "CONNECT":
            from django.http import HttpResponseBadRequest

            return HttpResponseBadRequest("Proxy requests are not allowed")

        # Filter requests with suspicious Host headers (common in proxy attacks)
        # Check HTTP_HOST header directly to avoid DisallowedHost exception
        host = request.META.get("HTTP_HOST", "")

        # Check if host looks like a proxy target (contains port and is not our domain)
        if (
            host
            and ":" in host
            and "convertica.net" not in host.lower()
            and "localhost" not in host.lower()
            and "127.0.0.1" not in host
        ):
            # This is likely a proxy CONNECT request that got through
            # Return 400 without raising DisallowedHost
            from django.http import HttpResponseBadRequest

            return HttpResponseBadRequest("Invalid request")

        return None
