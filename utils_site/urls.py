from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.staticfiles.finders import find
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from src.frontend.i18n_views import set_language
from src.frontend.views import index_page, sitemap_index, sitemap_lang
from src.frontend.views_indexnow import indexnow_key_file
from src.frontend.views_seo import favicon_view, robots_txt_view
from src.payments.views import stripe_webhook

from utils_site.swagger import schema_view


@require_http_methods(["GET"])
def liveness_check(request):
    """Simple liveness check - just confirms the app is running.

    Used for Docker healthcheck to detect if the process is alive.
    Does NOT check external dependencies (DB, Redis) to avoid false negatives.
    """
    return HttpResponse("OK", content_type="text/plain", status=200)


@require_http_methods(["GET"])
def health_check(request):
    """Full health check endpoint for Docker and load balancers.

    Checks database and cache connectivity.
    Use /livez/ for simple liveness checks that don't depend on external services.
    """
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


@require_http_methods(["GET"])
def service_worker(request):
    sw_path = find("sw.js")
    if not sw_path:
        return HttpResponse("Not found", content_type="text/plain", status=404)

    with open(sw_path, "rb") as f:
        content = f.read()

    response = HttpResponse(content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("api/", include("src.api.urls")),
    path("i18n/setlang/", set_language, name="set_language"),
    path("payments/webhook/", stripe_webhook, name="stripe_webhook"),
    path(
        "offline.html", lambda request: render(request, "offline.html"), name="offline"
    ),
    path("sw.js", service_worker, name="service_worker"),
    # Favicon - serve from static files
    path("favicon.ico", favicon_view, name="favicon"),
    # IndexNow key file for search engine verification
    path(
        f"{getattr(settings, 'INDEXNOW_KEY', 'indexnow-key')}.txt",
        indexnow_key_file,
        name="indexnow_key",
    ),
    # robots.txt can be served by nginx, but Django keeps a fallback for app-only setups
    path("robots.txt", robots_txt_view, name="robots_txt"),
    path("health/", health_check, name="health_check"),
    path("livez/", liveness_check, name="liveness_check"),
    # SEO - sitemaps should be accessible without language prefix
    path("sitemap.xml", sitemap_index, name="sitemap_index"),
    path("sitemap-<str:lang>.xml", sitemap_lang, name="sitemap_lang"),
    # Admin panel - should be accessible without language prefix
    # Read ADMIN_URL_PATH dynamically from settings
    path(f"{getattr(settings, 'ADMIN_URL_PATH', 'admin')}/", admin.site.urls),
    # Homepage - accessible without language prefix for SEO
    path("", index_page, name="index_page"),
]

# Prometheus metrics endpoint (only if django-prometheus is installed)
try:
    import django_prometheus

    urlpatterns.append(path("metrics/", include("django_prometheus.urls")))
except ImportError:
    pass

urlpatterns += i18n_patterns(
    path("blog/", include("src.blog.urls")),
    path("users/", include("src.users.urls")),
    path("payments/", include("src.payments.urls")),
    path("", include("src.frontend.urls")),
)

# Add allauth URLs outside i18n_patterns
urlpatterns += [
    path("accounts/", include("allauth.urls")),
]

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
