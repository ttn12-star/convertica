"""Views for IndexNow integration."""

from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from .indexnow import get_indexnow_key_content


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24 * 7)  # Cache for 7 days
def indexnow_key_file(request):
    """
    Serve IndexNow key file.

    This file must be accessible at the root of the domain to verify ownership.
    Example: https://convertica.net/a1b2c3d4e5f6.txt
    """
    key_content = get_indexnow_key_content()
    if not key_content:
        return HttpResponse("IndexNow key not configured", status=404)

    return HttpResponse(key_content, content_type="text/plain; charset=utf-8")
