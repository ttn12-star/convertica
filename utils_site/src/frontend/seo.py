"""SEO helpers for canonical URLs, robots directives, and hreflang links."""

from __future__ import annotations

from urllib.parse import urlencode

from decouple import config
from django.conf import settings
from django.urls import Resolver404, resolve, reverse
from django.utils.translation import activate, get_language

from .i18n_views import remove_all_language_prefixes

INDEX_ROBOTS = (
    "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
)
NOINDEX_FOLLOW_ROBOTS = "noindex, follow"
NOINDEX_NOFOLLOW_ROBOTS = "noindex, nofollow"

NOINDEX_PATH_PREFIXES = (
    "/users/",
    "/accounts/",
    "/payments/",
)
NOINDEX_EXACT_PATHS = {
    "/contribute/success/",
}


def get_base_url(request) -> str:
    """Build the canonical site base URL for the current request."""
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    if getattr(settings, "DEBUG", False):
        return f"{scheme}://{request.get_host()}"

    site_domain = config("SITE_DOMAIN", default=None)
    return f"{scheme}://{site_domain or request.get_host()}"


def get_request_seo_context(request) -> dict:
    """Compute and cache SEO metadata for the current request."""
    cached = getattr(request, "_seo_context", None)
    if cached is not None:
        return cached

    languages = getattr(settings, "LANGUAGES", [("en", "English")])
    default_language = settings.LANGUAGE_CODE
    homepage_paths = [f"/{code}/" for code, _ in languages]
    base_url = get_base_url(request)
    view_name, url_kwargs = _resolve_view(request)
    normalized_path = remove_all_language_prefixes(request.path)
    is_homepage = request.path == "/" or request.path in homepage_paths
    canonical_path = "/" if is_homepage else request.path

    robots_meta = INDEX_ROBOTS
    hreflangs_enabled = True
    canonical_url = None
    canonical_query: dict[str, str] = {}

    if _is_non_indexable_path(normalized_path):
        robots_meta = NOINDEX_NOFOLLOW_ROBOTS
        hreflangs_enabled = False
    else:
        canonical_url = f"{base_url}{canonical_path}"
        canonical_query, robots_override = _get_canonical_query_and_robots(
            request=request,
            view_name=view_name,
        )
        if robots_override is not None:
            robots_meta = robots_override
            hreflangs_enabled = False

        if canonical_query:
            canonical_url = f"{canonical_url}?{urlencode(canonical_query, doseq=True)}"

    hreflangs = _build_hreflang_links(
        request=request,
        view_name=view_name,
        url_kwargs=url_kwargs,
        base_url=base_url,
        languages=languages,
        default_language=default_language,
        homepage_paths=homepage_paths,
        hreflangs_enabled=hreflangs_enabled,
        canonical_query=canonical_query,
    )

    current_url = canonical_url or f"{base_url}{request.path}"

    cached = {
        "site_base_url": base_url,
        "site_current_url": current_url,
        "canonical_url": canonical_url,
        "robots_meta": robots_meta,
        "hreflangs": hreflangs,
        "hreflang_homepage_paths": homepage_paths,
        "default_language_code": default_language,
        "seo_view_name": view_name,
        "seo_normalized_path": normalized_path,
    }
    request._seo_context = cached
    return cached


def _resolve_view(request) -> tuple[str | None, dict]:
    """Resolve the current request to a Django view name and kwargs."""
    try:
        match = resolve(request.path)
        return match.view_name, match.kwargs
    except (Resolver404, AttributeError):
        return None, {}


def _is_non_indexable_path(normalized_path: str) -> bool:
    if normalized_path in NOINDEX_EXACT_PATHS:
        return True

    return any(normalized_path.startswith(prefix) for prefix in NOINDEX_PATH_PREFIXES)


def _get_canonical_query_and_robots(
    request, view_name: str | None
) -> tuple[dict, str | None]:
    """Return canonical query params and optional robots override."""
    if not request.GET:
        return {}, None

    query_keys = set(request.GET.keys())

    if view_name == "blog:article_list" and query_keys == {"page"}:
        page = request.GET.get("page", "").strip()
        if page.isdigit() and int(page) > 1:
            return {"page": str(int(page))}, None

    return {}, NOINDEX_FOLLOW_ROBOTS


def _build_hreflang_links(
    request,
    view_name: str | None,
    url_kwargs: dict,
    base_url: str,
    languages,
    default_language: str,
    homepage_paths: list[str],
    hreflangs_enabled: bool,
    canonical_query: dict[str, str],
) -> list[dict[str, str]]:
    """Build hreflang alternate links for indexable pages only."""
    if not hreflangs_enabled:
        return []

    is_homepage = request.path == "/" or request.path in homepage_paths
    if is_homepage:
        hreflangs = []
        for code, _ in languages:
            url = f"{base_url}/" if code == default_language else f"{base_url}/{code}/"
            hreflangs.append({"code": code, "url": url})
        hreflangs.append({"code": "x-default", "url": f"{base_url}/"})
        return hreflangs

    if not view_name:
        return []

    old_lang = get_language()
    hreflangs = []
    try:
        for code, _ in languages:
            activate(code)
            try:
                path = reverse(view_name, kwargs=url_kwargs)
            except Exception:
                path = _fallback_language_path(request.path, code, languages)

            url = f"{base_url}{path}"
            if canonical_query:
                url = f"{url}?{urlencode(canonical_query, doseq=True)}"
            hreflangs.append({"code": code, "url": url})

        activate(default_language)
        try:
            default_path = reverse(view_name, kwargs=url_kwargs)
        except Exception:
            default_path = _fallback_language_path(
                request.path, default_language, languages
            )

        default_url = f"{base_url}{default_path}"
        if canonical_query:
            default_url = f"{default_url}?{urlencode(canonical_query, doseq=True)}"
        hreflangs.append({"code": "x-default", "url": default_url})
    finally:
        activate(old_lang)

    return hreflangs


def _fallback_language_path(path: str, language_code: str, languages) -> str:
    """Fallback hreflang path builder when reverse() is unavailable."""
    cleaned_path = remove_all_language_prefixes(path)
    if cleaned_path == "/":
        return f"/{language_code}/"

    supported_codes = {code for code, _ in languages}
    parts = [part for part in cleaned_path.strip("/").split("/") if part]
    while parts and parts[0] in supported_codes:
        parts.pop(0)

    suffix = "/".join(parts)
    if not suffix:
        return f"/{language_code}/"
    return (
        f"/{language_code}/{suffix}/"
        if not suffix.endswith("/")
        else f"/{language_code}/{suffix}"
    )
