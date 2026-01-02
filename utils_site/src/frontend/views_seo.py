"""SEO-related views for favicon, robots.txt, etc."""

from django.contrib.staticfiles.finders import find
from django.http import FileResponse, HttpResponseNotFound
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24 * 7)  # Cache for 7 days
def favicon_view(request):  # noqa: ARG001
    """Serve favicon.ico from static files."""
    favicon_path = find("favicon.ico")
    if not favicon_path:
        return HttpResponseNotFound("Favicon not found")

    return FileResponse(
        open(favicon_path, "rb"), content_type="image/x-icon"  # noqa: SIM115
    )
