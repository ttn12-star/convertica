"""Admin protection middleware and decorators."""

import logging
from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.http import HttpRequest, HttpResponseForbidden

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")

    # Log for debugging
    logger.debug(
        f"Client IP detection - X-Forwarded-For: {x_forwarded_for}, "
        f"REMOTE_ADDR: {request.META.get('REMOTE_ADDR', '')}, "
        f"Final IP: {ip}"
    )

    return ip


class AdminIPWhitelistMiddleware:
    """
    Middleware to restrict admin access to whitelisted IP addresses.

    Add to settings.py:
    ADMIN_IP_WHITELIST = ['127.0.0.1', '::1', 'your.ip.address']
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get admin URL path from settings
        admin_path = getattr(settings, "ADMIN_URL_PATH", "admin")
        admin_url = f"/{admin_path}/"

        # Only check for admin URLs
        if request.path.startswith(admin_url):
            # Get whitelist from settings
            whitelist = getattr(settings, "ADMIN_IP_WHITELIST", [])

            # If whitelist is empty, allow all (for development)
            if not whitelist:
                logger.debug("Admin IP whitelist is empty, allowing access")
                return self.get_response(request)

            # Get client IP
            client_ip = get_client_ip(request)

            # Log access attempt
            logger.info(
                f"Admin access attempt - IP: {client_ip}, "
                f"Path: {request.path}, "
                f"Whitelist: {whitelist}, "
                f"Allowed: {client_ip in whitelist}"
            )

            # Check if IP is whitelisted
            if client_ip not in whitelist:
                logger.warning(
                    f"Admin access denied - IP {client_ip} not in whitelist {whitelist}. "
                    f"REMOTE_ADDR: {request.META.get('REMOTE_ADDR', 'N/A')}, "
                    f"X-Forwarded-For: {request.META.get('HTTP_X_FORWARDED_FOR', 'N/A')}"
                )
                return HttpResponseForbidden(
                    f"<h1>403 Forbidden</h1>"
                    f"<p>Access to admin panel is restricted.</p>"
                    f"<p>Your IP: {client_ip}</p>"
                    f"<p>Whitelist: {', '.join(whitelist)}</p>",
                    content_type="text/html",
                )

            logger.debug(f"Admin access allowed for IP: {client_ip}")

        return self.get_response(request)


def admin_ip_required(view_func: Callable) -> Callable:
    """
    Decorator to restrict admin views to whitelisted IPs.

    Usage:
        @admin_ip_required
        def admin_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        whitelist = getattr(settings, "ADMIN_IP_WHITELIST", [])

        if whitelist:
            client_ip = get_client_ip(request)
            if client_ip not in whitelist:
                return HttpResponseForbidden(
                    "<h1>403 Forbidden</h1><p>Access denied.</p>",
                    content_type="text/html",
                )

        return view_func(request, *args, **kwargs)

    return wrapper
