"""SEO-related views for favicon, robots.txt, etc."""

from decouple import config
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
    site_domain = config("SITE_DOMAIN", default=request.get_host())

    if robots_path:
        with open(robots_path, encoding="utf-8") as robots_file:
            content = robots_file.read()
    else:
        content = _fallback_robots_content()

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
    """Last-resort robots.txt when the static asset is unavailable at runtime.

    Keep in sync with static/robots.txt (the single source of truth) — a
    drifted fallback silently un-blocks premium/batch paths.
    """
    return """User-agent: *
Allow: /

# Duplicate URL variants and internal search/filter combinations
Disallow: /*?lang=*
Disallow: /*&lang=*
Disallow: /*?q=*
Disallow: /*&q=*
Disallow: /*?category=*
Disallow: /*&category=*

# NB: double language-prefix URLs (e.g. /es/ru/...) are intentionally NOT
# blocked here. DoubleLanguagePrefixMiddleware 301-redirects them to the
# canonical single-prefix URL, which consolidates them cleanly. A robots
# block only froze them as stale 404s in Search Console (Google can't recrawl
# a disallowed URL to see the 301). Let the redirect do the work.

# Disallow API endpoints and static admin assets
# (real admin is hidden behind an obscured path + IP whitelist;
# we don't advertise it in robots.txt)
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

# Disallow premium-gated tools that 302-redirect anonymous visitors to login
# (kept off the public crawl to avoid noisy 302→login chains in audits).
# /scanned-pdf-to-word/ is intentionally NOT blocked: OCR is a high-CPC
# keyword we want indexed. The landing page must serve crawlable anonymous
# content; the actual conversion remains premium-gated at the app layer.
Disallow: /batch-converter/
Disallow: /*/batch-converter/
Disallow: /premium/
Disallow: /*/premium/

# Explicit Allow guard: the crawlable premium CATALOG page shares the
# "premium" slug prefix and survives the block above only because of the
# trailing slash in "Disallow: /premium/". Keep these Allow lines so a future
# broadening of that block can never silently de-index the catalog.
Allow: /premium-tools/
Allow: /*/premium-tools/

# Disallow Cloudflare email-protection endpoint (404 on our plan, surfaces
# as a broken link from any mailto: in the page)
Disallow: /cdn-cgi/

# Allow pricing page for SEO
Allow: /pricing/
Allow: /*/pricing/

# Allow static files
Allow: /static/
Allow: /media/

# Sitemap
Sitemap: https://convertica.net/sitemap.xml
"""
