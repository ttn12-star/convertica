from pathlib import Path

from decouple import config
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.views.i18n import set_language
from src.frontend.views import sitemap_index, sitemap_lang

from utils_site.swagger import schema_view


@require_http_methods(["GET"])
@cache_page(3600, key_prefix="robots_txt")
def robots_txt(request):
    """Serve robots.txt file with dynamic sitemap URL and admin path."""
    robots_path = Path(__file__).resolve().parent.parent / "static" / "robots.txt"

    # Determine scheme: prefer X-Forwarded-Proto (from Nginx), fallback to request.scheme
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    # Force HTTPS in production (if not DEBUG)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    # Use production domain instead of IP address for robots.txt
    # Fallback to request.get_host() if SITE_DOMAIN not set
    site_domain = config("SITE_DOMAIN", default=None)
    if site_domain:
        base_url = f"{scheme}://{site_domain}"
    else:
        base_url = f"{scheme}://{request.get_host()}"
    admin_path = getattr(settings, "ADMIN_URL_PATH", "admin")

    # Fallback content in case of any errors
    fallback_content = f"User-agent: *\nAllow: /\n\n# Disallow admin and API endpoints\nDisallow: /{admin_path}/\nDisallow: /api/\n\n# Sitemap\nSitemap: {base_url}/sitemap.xml\n"

    try:
        # Try to read the static robots.txt file
        if robots_path.exists() and robots_path.is_file():
            with open(robots_path, encoding="utf-8") as f:
                content = f.read()

            # Replace hardcoded sitemap URL with dynamic one (handle both http and https)
            content = content.replace(
                "https://convertica.net/sitemap.xml", f"{base_url}/sitemap.xml"
            )
            content = content.replace(
                "http://convertica.net/sitemap.xml", f"{base_url}/sitemap.xml"
            )
            # Replace hardcoded admin path with dynamic one
            content = content.replace("/admin/", f"/{admin_path}/")
            return HttpResponse(content, content_type="text/plain")
        else:
            # File doesn't exist, use fallback without logging error
            return HttpResponse(fallback_content, content_type="text/plain")
    except Exception:
        # Use fallback content for any errors (file read errors, encoding issues, etc.)
        # Don't log to Sentry - this is not a critical error
        return HttpResponse(fallback_content, content_type="text/plain")


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for Docker and load balancers."""
    from django.core.cache import cache
    from django.db import connection

    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Check cache connection
        cache.set("health_check", "ok", 10)
        cache.get("health_check")

        return HttpResponse("OK", content_type="text/plain", status=200)
    except Exception as e:
        return HttpResponse(f"ERROR: {str(e)}", content_type="text/plain", status=503)


urlpatterns = [
    path("api/", include("src.api.urls")),
    path("i18n/setlang/", set_language, name="set_language"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("health/", health_check, name="health_check"),
    # SEO - sitemaps should be accessible without language prefix
    path("sitemap.xml", sitemap_index, name="sitemap_index"),
    path("sitemap-<str:lang>.xml", sitemap_lang, name="sitemap_lang"),
    # Admin panel - should be accessible without language prefix
    # Read ADMIN_URL_PATH dynamically from settings
    path(f"{getattr(settings, 'ADMIN_URL_PATH', 'admin')}/", admin.site.urls),
]

# Prometheus metrics endpoint (only if django-prometheus is installed)
try:
    import django_prometheus

    urlpatterns.append(path("metrics/", include("django_prometheus.urls")))
except ImportError:
    pass

urlpatterns += i18n_patterns(
    path("blog/", include("src.blog.urls")),
    path("", include("src.frontend.urls")),
)

if settings.DEBUG:
    urlpatterns += [
        path(
            "swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
    ]


# Custom error handlers with aggressive caching
# Cache error pages for 1 hour (3600 seconds) to reduce server load
# Error pages are static and don't change often
@cache_page(3600, key_prefix="error_400")
def handler400(request, exception):  # noqa: ARG001
    """Custom 400 error handler with caching."""
    response = render(request, "400.html", status=400)
    # Add noindex to prevent search engines from indexing error pages
    response["X-Robots-Tag"] = "noindex, nofollow"
    # Aggressive caching headers
    response["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return response


@cache_page(3600, key_prefix="error_403")
def handler403(request, exception):  # noqa: ARG001
    """Custom 403 error handler with caching."""
    response = render(request, "403.html", status=403)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return response


@cache_page(3600, key_prefix="error_404")
def handler404(request, exception):  # noqa: ARG001
    """Custom 404 error handler with caching."""
    response = render(request, "404.html", status=404)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return response


@cache_page(3600, key_prefix="error_500")
def handler500(request):  # noqa: ARG001
    """Custom 500 error handler with caching."""
    response = render(request, "500.html", status=500)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return response


@cache_page(3600, key_prefix="error_502")
def handler502(request):  # noqa: ARG001
    """Custom 502 error handler with caching."""
    response = render(request, "502.html", status=502)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return response
