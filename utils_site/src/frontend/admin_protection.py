"""Admin protection middleware and decorators."""
from django.http import HttpRequest, HttpResponseForbidden
from django.conf import settings
from functools import wraps
from typing import Callable


def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
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
        admin_path = getattr(settings, 'ADMIN_URL_PATH', 'admin')
        admin_url = f'/{admin_path}/'
        
        # Only check for admin URLs
        if request.path.startswith(admin_url):
            # Get whitelist from settings
            whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', [])
            
            # If whitelist is empty, allow all (for development)
            if not whitelist:
                return self.get_response(request)
            
            # Get client IP
            client_ip = get_client_ip(request)
            
            # Check if IP is whitelisted
            if client_ip not in whitelist:
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1><p>Access to admin panel is restricted.</p>',
                    content_type='text/html'
                )
        
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
        whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', [])
        
        if whitelist:
            client_ip = get_client_ip(request)
            if client_ip not in whitelist:
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1><p>Access denied.</p>',
                    content_type='text/html'
                )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

