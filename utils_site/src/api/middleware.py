"""
API middleware for rate limiting and performance monitoring.
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import time

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
        if not request.path.startswith('/api/'):
            return None
        
        # Skip rate limiting if cache is not available
        if not CACHE_AVAILABLE:
            return None
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Rate limit key
        rate_limit_key = f'rate_limit:{ip}'
        
        try:
            # Get current count
            current_count = cache.get(rate_limit_key, 0)
            
            # Check limit (100 requests per minute)
            if current_count >= 100:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please try again later.',
                    },
                    status=429
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
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            response['X-Process-Time'] = f'{duration:.3f}'
            
            # Log slow requests (> 1 second)
            if duration > 1.0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Slow request: {request.path} took {duration:.3f}s"
                )
        
        return response

