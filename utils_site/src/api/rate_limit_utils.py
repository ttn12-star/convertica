"""
Rate limiting utilities with premium user support.
Provides decorators and helpers for combined IP + User rate limiting.
"""

import logging
from functools import wraps

from django.core.cache import cache
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


def get_user_rate_limit(group, request):
    """
    Dynamic rate limit based on user premium status.

    Args:
        group: Rate limit group name
        request: Django request object

    Returns:
        Rate limit string (e.g., '1000/h', '10000/h')
    """
    premium_rates = {
        "api_conversion": "10000/h",
        "api_batch": "500/h",
        "api_auth": "100/h",
    }
    authenticated_rates = {
        "api_conversion": "1000/h",
        "api_batch": "50/h",
        "api_auth": "50/h",
    }
    anonymous_rates = {
        "api_conversion": "100/h",
        "api_batch": "0/h",
        "api_auth": "20/h",
    }

    if request.user.is_authenticated:
        try:
            from .premium_utils import is_premium_active

            if is_premium_active(request.user):
                return premium_rates.get(group, "5000/h")
            return authenticated_rates.get(group, "500/h")
        except Exception as e:
            logger.warning(f"Error checking premium status: {e}")
            return authenticated_rates.get(group, "500/h")

    return anonymous_rates.get(group, "50/h")


def combined_rate_limit(group="api", ip_rate="100/h", methods=None):
    """
    Decorator for combined IP + User rate limiting.

    Usage:
        @combined_rate_limit(group='api_conversion', ip_rate='100/h', methods=['POST'])
        def my_api_view(request):
            pass

    Args:
        group: Rate limit group name (used for user-based limits)
        ip_rate: IP-based rate limit (applies to all users from same IP)
        methods: HTTP methods to rate limit (default: ['POST'])

    Returns:
        Decorated function with combined rate limiting
    """
    if methods is None:
        methods = ["POST"]

    method_str = ",".join(methods) if isinstance(methods, list) else methods

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Support both function-based views (request, ...) and CBV methods (self, request, ...)
            self_obj = None
            request = kwargs.get("request")
            remaining_args = args

            if request is None:
                if args and hasattr(args[0], "META") and hasattr(args[0], "method"):
                    request = args[0]
                    remaining_args = args[1:]
                elif (
                    len(args) >= 2
                    and hasattr(args[1], "META")
                    and hasattr(args[1], "method")
                ):
                    self_obj = args[0]
                    request = args[1]
                    remaining_args = args[2:]
            else:
                # If request was provided explicitly, the first arg can still be self in CBV.
                if args and not (
                    hasattr(args[0], "META") and hasattr(args[0], "method")
                ):
                    self_obj = args[0]
                    remaining_args = args[1:]

            def call_original(req, *a, **kw):
                if self_obj is not None:
                    return func(self_obj, req, *a, **kw)
                return func(req, *a, **kw)

            # Apply rate limits to a callable where request is the first argument.
            limited = ratelimit(
                key="ip",
                rate=ip_rate,
                method=method_str,
                block=True,
            )(
                ratelimit(
                    key="user_or_ip",
                    rate=get_user_rate_limit,
                    group=group,
                    method=method_str,
                    block=True,
                )(call_original)
            )

            # Log rate limit hits (best-effort, should never break the request)
            try:
                if request is not None:
                    _log_rate_limit_usage(request, group)
            except Exception as e:
                logger.error(f"Error logging rate limit usage: {e}")

            return limited(request, *remaining_args, **kwargs)

        return wrapper

    return decorator


def _log_rate_limit_usage(request, group):
    """
    Log rate limit usage for monitoring.

    Args:
        request: Django request object
        group: Rate limit group name
    """
    # Get user identifier
    if request.user.is_authenticated:
        user_id = request.user.id
        try:
            from .premium_utils import is_premium_active

            is_premium = is_premium_active(request.user)
        except Exception:
            is_premium = False
    else:
        user_id = "anonymous"
        is_premium = False

    # Get IP
    ip = _get_client_ip(request)

    # Increment counters in cache
    cache_key_prefix = f"rate_limit_stats:{group}"

    # Total requests
    total_key = f"{cache_key_prefix}:total"
    cache.add(total_key, 0, timeout=3600)
    cache.incr(total_key, 1)

    # Requests by user type
    if is_premium:
        premium_key = f"{cache_key_prefix}:premium"
        cache.add(premium_key, 0, timeout=3600)
        cache.incr(premium_key, 1)
    elif request.user.is_authenticated:
        auth_key = f"{cache_key_prefix}:authenticated"
        cache.add(auth_key, 0, timeout=3600)
        cache.incr(auth_key, 1)
    else:
        anon_key = f"{cache_key_prefix}:anonymous"
        cache.add(anon_key, 0, timeout=3600)
        cache.incr(anon_key, 1)

    # Log to file for analysis
    logger.info(
        f"Rate limit usage: group={group}, user={user_id}, "
        f"premium={is_premium}, ip={ip}, endpoint={request.path}"
    )


def _get_client_ip(request):
    """
    Get client IP address from request.

    Args:
        request: Django request object

    Returns:
        Client IP address string
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_rate_limit_stats(group=None, hours=1):
    """
    Get rate limit statistics for monitoring.

    Args:
        group: Rate limit group name (None for all groups)
        hours: Number of hours to look back

    Returns:
        Dictionary with rate limit statistics
    """
    stats = {}

    if group:
        groups = [group]
    else:
        groups = ["api_conversion", "api_batch", "api_auth", "api_other"]

    for grp in groups:
        cache_key_prefix = f"rate_limit_stats:{grp}"

        stats[grp] = {
            "total": cache.get(f"{cache_key_prefix}:total", 0),
            "premium": cache.get(f"{cache_key_prefix}:premium", 0),
            "authenticated": cache.get(f"{cache_key_prefix}:authenticated", 0),
            "anonymous": cache.get(f"{cache_key_prefix}:anonymous", 0),
            "blocked_ip": cache.get(f"{cache_key_prefix}:blocked_ip", 0),
            "blocked_user": cache.get(f"{cache_key_prefix}:blocked_user", 0),
        }

    return stats


def log_rate_limit_block(request, limit_type="ip"):
    """
    Log when a request is blocked by rate limiting.

    Args:
        request: Django request object
        limit_type: Type of limit that blocked ('ip' or 'user')
    """
    user_id = request.user.id if request.user.is_authenticated else "anonymous"
    ip = _get_client_ip(request)

    logger.warning(
        f"Rate limit BLOCKED: type={limit_type}, user={user_id}, "
        f"ip={ip}, endpoint={request.path}, method={request.method}"
    )

    # Increment blocked counter
    cache_key = f"rate_limit_stats:blocked_{limit_type}"
    cache.add(cache_key, 0, timeout=3600)
    cache.incr(cache_key, 1)


# Custom exception handler for rate limit errors
def handle_rate_limit_exception(request, exception):
    """
    Custom handler for Ratelimited exceptions.

    Args:
        request: Django request object
        exception: Ratelimited exception

    Returns:
        JSON response with rate limit error
    """
    from django.http import JsonResponse

    # Determine which limit was hit
    limit_type = "ip" if "ip" in str(exception) else "user"

    # Log the block
    log_rate_limit_block(request, limit_type)

    # Get user-friendly message
    if request.user.is_authenticated:
        if hasattr(request.user, "premium") and request.user.premium.is_active:
            message = "You've reached your premium rate limit. Please try again in a few minutes."
        else:
            message = (
                "You've reached your rate limit. "
                "Upgrade to Premium for 10x higher limits! "
                "Only $4.99/month or $1/day."
            )
    else:
        message = (
            "Rate limit exceeded. "
            "Please sign in for higher limits or upgrade to Premium for unlimited access!"
        )

    return JsonResponse(
        {
            "error": "Rate limit exceeded",
            "message": message,
            "limit_type": limit_type,
            "retry_after": 60,  # Suggest retry after 60 seconds
        },
        status=429,
    )


# Middleware to track rate limit hits
class RateLimitMonitoringMiddleware:
    """
    Middleware to monitor rate limit hits and blocks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Check if response is 429 (rate limited)
        if response.status_code == 429:
            # Determine limit type from response
            limit_type = "user" if request.user.is_authenticated else "ip"
            log_rate_limit_block(request, limit_type)

        return response
