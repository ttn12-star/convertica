"""
Core middleware for the Convertica application.
"""

from django.utils.deprecation import MiddlewareMixin


class DisableLocaleForSitemapMiddleware(MiddlewareMixin):
    """
    Disable locale middleware for sitemap.xml requests.

    This middleware removes locale-related headers and settings for sitemap requests
    to ensure consistent XML output regardless of user language preferences.
    """

    def process_request(self, request):
        """Disable locale processing for sitemap requests."""
        if request.path == "/sitemap.xml":
            # Remove language code from request
            request.LANGUAGE_CODE = None

    def process_response(self, request, response):
        """Remove locale-related headers from sitemap response."""
        if request.path == "/sitemap.xml":
            # Remove locale-related headers that might affect caching
            response.headers.pop("Content-Language", None)
            response.headers.pop("Vary", None)

        return response


class DisableSessionForSitemapMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/sitemap.xml":
            request._dont_use_session = True
        response = self.get_response(request)
        if request.path == "/sitemap.xml":
            response.cookies.clear()
            if "Vary" in response.headers:
                del response.headers["Vary"]
        return response
