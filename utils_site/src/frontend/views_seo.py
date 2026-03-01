"""SEO-related views for favicon, robots.txt, etc."""

from decouple import config
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.http import FileResponse, HttpResponse, HttpResponseNotFound
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
        open(favicon_path, "rb"),
        content_type="image/x-icon",  # noqa: SIM115
    )


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24)  # Cache for 1 day
def robots_txt_view(request):  # noqa: ARG001
    """Serve robots.txt with environment-aware sitemap and admin URLs."""
    robots_path = find("robots.txt")
    admin_path = getattr(settings, "ADMIN_URL_PATH", "admin")
    site_domain = config("SITE_DOMAIN", default=request.get_host())

    if robots_path:
        with open(robots_path, encoding="utf-8") as robots_file:
            content = robots_file.read()
    else:
        content = _fallback_robots_content()

    content = content.replace("/__ADMIN_PATH__/", f"/{admin_path}/")
    content = content.replace(
        "https://convertica.net/sitemap.xml",
        f"https://{site_domain}/sitemap.xml",
    )
    content = content.replace(
        "http://convertica.net/sitemap.xml",
        f"https://{site_domain}/sitemap.xml",
    )

    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def _fallback_robots_content() -> str:
    """Return a safe fallback robots.txt when the static asset is unavailable."""
    return """User-agent: *
Allow: /

# Duplicate URL variants and internal search/filter combinations
Disallow: /*?lang=*
Disallow: /*&lang=*
Disallow: /*?q=*
Disallow: /*&q=*
Disallow: /*?category=*
Disallow: /*&category=*

# Disallow admin and API endpoints
Disallow: /__ADMIN_PATH__/
Disallow: /api/
Disallow: /static/admin/

# Disallow user authentication and account pages
Disallow: /users/
Disallow: /*/users/
Disallow: /accounts/
Disallow: /*/accounts/

# Disallow payment and post-conversion success pages
Disallow: /payments/
Disallow: /*/payments/
Disallow: /contribute/success/
Disallow: /*/contribute/success/

Sitemap: https://convertica.net/sitemap.xml
"""
