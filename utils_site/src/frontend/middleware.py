"""
Custom middleware for frontend.
"""

import hashlib
import logging
import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.translation import activate

logger = logging.getLogger(__name__)


class AutoLanguageMiddleware:
    """
    Automatically detect and set user's language preference.
    Only activates if language is not already explicitly set in session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only auto-detect if language is not already in session
        # (i.e., user hasn't explicitly chosen a language)
        # Safely check for session - it may not be available in some edge cases
        if hasattr(request, "session") and "django_language" not in request.session:
            # Try to detect language from Accept-Language header
            accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")

            if accept_language:
                # Parse Accept-Language header
                # Format: "en-US,en;q=0.9,ru;q=0.8"
                languages = []
                for lang_item in accept_language.split(","):
                    lang_item = lang_item.strip()
                    if ";" in lang_item:
                        lang_code = lang_item.split(";")[0].strip()
                    else:
                        lang_code = lang_item.strip()

                    # Extract base language code (e.g., 'en' from 'en-US')
                    base_lang = lang_code.split("-")[0].lower()

                    # Check if this language is supported
                    supported_codes = [code for code, _ in settings.LANGUAGES]
                    if base_lang in supported_codes:
                        languages.append(base_lang)

                # Use first supported language
                if languages:
                    detected_language = languages[0]
                    request.session["django_language"] = detected_language
                    activate(detected_language)
                    logger.debug(f"Auto-detected language: {detected_language}")

        response = self.get_response(request)
        return response


class DoubleLanguagePrefixMiddleware:
    """
    Redirect URLs with double language prefixes (e.g., /en/pl/...) to correct URLs.
    This prevents Google from indexing invalid URLs with multiple language codes.

    Additionally adds X-Robots-Tag: noindex to the redirect response to tell search
    engines not to index these malformed URLs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Check if path has multiple language prefixes
        # Example: /en/pl/pdf-organize/merge/ -> /pl/pdf-organize/merge/
        if path and path.startswith("/"):
            path_parts = path.strip("/").split("/")
            if len(path_parts) >= 2:
                supported_languages = [code for code, _ in settings.LANGUAGES]

                # Count how many consecutive language prefixes we have
                lang_prefix_count = 0
                for part in path_parts:
                    if part in supported_languages:
                        lang_prefix_count += 1
                    else:
                        break

                # If we have 2+ language prefixes, redirect to correct URL
                if lang_prefix_count >= 2:
                    # Remove all language prefixes and keep only the last one
                    # This handles cases like /en/pl/ru/... -> /ru/...
                    remaining_parts = path_parts[lang_prefix_count - 1 :]
                    corrected_path = "/" + "/".join(remaining_parts)
                    if not corrected_path.endswith("/") and path.endswith("/"):
                        corrected_path += "/"

                    # Preserve query string
                    query_string = request.META.get("QUERY_STRING", "")
                    if query_string:
                        corrected_path += f"?{query_string}"

                    logger.warning(
                        "Multiple language prefixes detected (%s): %s -> redirecting to %s | ip=%s referer=%s ua=%s query=%s",
                        lang_prefix_count,
                        path,
                        corrected_path,
                        request.META.get("REMOTE_ADDR", ""),
                        request.META.get("HTTP_REFERER", ""),
                        request.META.get("HTTP_USER_AGENT", ""),
                        request.META.get("QUERY_STRING", ""),
                    )

                    # Create redirect response with noindex header
                    # This tells Google and other search engines not to index this URL
                    response = HttpResponsePermanentRedirect(corrected_path)
                    response["X-Robots-Tag"] = "noindex, nofollow"
                    return response

        response = self.get_response(request)
        return response


class CaptchaRequirementMiddleware:
    """
    Track failed attempts and require CAPTCHA after multiple failures.

    Uses both session-based (for users with cookies) and IP-based (for cookie-less requests)
    tracking to prevent spam attacks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only track CAPTCHA requirement for API calls.
        # Avoid creating/modifying sessions for anonymous users just browsing pages.
        # This check is done PRE-response so we can short-circuit and save backend work.
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # Origin/Referer gate: legitimate web traffic always carries a Referer
        # from convertica.net (browsers attach it automatically on form POST and
        # fetch() unless an explicit no-referrer policy is set, which we don't).
        # Calls without it are almost always scripts (curl, python-requests, …).
        # Demand CAPTCHA immediately — no 3-fails grace.
        allowed_origins = (
            "https://convertica.net",
            "http://convertica.net",  # for local dev/probes
            f"https://{getattr(settings, 'SITE_DOMAIN', 'convertica.net')}",
        )
        referer = request.META.get("HTTP_REFERER", "")
        origin = request.META.get("HTTP_ORIGIN", "")
        has_first_party_referer = any(
            (
                referer == o
                or referer.startswith(o + "/")
                or origin == o
                or origin.startswith(o + "/")
            )
            for o in allowed_origins
        )
        if (
            not has_first_party_referer
            and not settings.DEBUG
            and not getattr(settings, "TESTING", False)
        ):
            if hasattr(request, "session"):
                request.session["captcha_required"] = True
                logger.info(
                    "CAPTCHA required (origin gate: ref=%r orig=%r)",
                    referer,
                    origin,
                )

        response = self.get_response(request)

        # Get client IP for IP-based tracking (works even without session)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        # Track failed attempts in session (if available)
        # Note: We track 429 (rate limit) and 400 (spam protection) as failed attempts
        # because excessive requests or spam behavior should trigger CAPTCHA requirement
        if hasattr(request, "session"):
            # Check if this was a failed request (429 or 400 from spam protection)
            if hasattr(response, "status_code"):
                if response.status_code in [429, 400]:
                    # Increment failed attempts in session
                    failed_attempts = request.session.get("failed_attempts", 0) + 1
                    request.session["failed_attempts"] = failed_attempts

                    # Require CAPTCHA after 3 failed attempts (skip in DEBUG mode)
                    if (
                        failed_attempts >= 3
                        and not settings.DEBUG
                        and not getattr(settings, "TESTING", False)
                    ):
                        request.session["captcha_required"] = True
                        logger.info(
                            f"CAPTCHA required for IP {ip} (session-based) after {request.session['failed_attempts']} failed attempts"
                        )
                else:
                    # Reset on successful request (2xx or 3xx status codes)
                    # This allows legitimate users to recover from false positives
                    if request.session.get("failed_attempts", 0) > 0:
                        request.session.pop("failed_attempts", None)
                        request.session.pop("captcha_required", None)

        # Also track failed attempts by IP (for cookie-less spam protection)
        # This provides protection even when sessions are disabled or cookies blocked
        if hasattr(response, "status_code"):
            from django.core.cache import cache

            if response.status_code in [429, 400]:
                # Increment IP-based failed attempts counter
                ip_failed_key = f"captcha_failed_attempts_ip:{ip}"
                ip_captcha_key = f"captcha_required_ip:{ip}"
                try:
                    ip_failed_count = cache.get(ip_failed_key, 0) + 1
                    cache.set(ip_failed_key, ip_failed_count, 3600)  # 1 hour TTL

                    # Require CAPTCHA after 3 failed attempts (same as session-based)
                    if (
                        ip_failed_count >= 3
                        and not settings.DEBUG
                        and not getattr(settings, "TESTING", False)
                    ):
                        cache.set(ip_captcha_key, True, 3600)  # Remember for 1 hour
                        logger.info(
                            f"CAPTCHA required for IP {ip} (IP-based) after {ip_failed_count} failed attempts"
                        )
                except Exception as e:
                    logger.error(
                        f"Error tracking IP-based failed attempts: {str(e)}",
                        exc_info=True,
                    )
            else:
                # Reset IP-based failed attempts counter on successful request
                # Successful request means user is legitimate - allow recovery
                # Note: We only reset failed_attempts counter, not captcha_required flag.
                # The captcha_required flag should only be cleared by explicit CAPTCHA verification
                # in spam_protection.py, or by TTL expiration, to maintain security.
                ip_failed_key = f"captcha_failed_attempts_ip:{ip}"
                try:
                    # Reset failed attempts counter on successful request
                    # This allows legitimate users to recover from false positives
                    if cache.get(ip_failed_key):
                        cache.delete(ip_failed_key)
                except Exception:
                    pass

        return response


# --- Consent-free traffic counting -----------------------------------------

# Substrings that mark a request as a bot/crawler/monitor rather than a real
# visitor. We host heavy crawl traffic (Bing/Google/Ahrefs/…), so without this
# the "real users" number would be dominated by robots.
_BOT_UA_RE = re.compile(
    r"bot|crawl|spider|slurp|bing|google|yandex|baidu|duckduck|ahrefs|semrush|"
    r"mj12|dotbot|petalbot|facebookexternalhit|embedly|preview|monitor|pingdom|"
    r"uptime|headless|phantom|python-requests|curl|wget|scrapy|httpx|okhttp",
    re.IGNORECASE,
)

# Path prefixes that are never real page views.
# /offline.html is the PWA service-worker fallback shell, not a visited page —
# it was showing up as a top "page" and inflating the count.
_SKIP_PREFIXES = (
    "/admin",
    "/api",
    "/static",
    "/media",
    "/ws",
    "/.well-known",
    "/offline.html",
)

# HyperLogLog keys are kept ~400 days so a full year of history is queryable.
_UV_TTL_SECONDS = 400 * 86400


def _redis():
    """Raw Redis client for HyperLogLog ops, or None if unavailable."""
    try:
        from django_redis import get_redis_connection

        return get_redis_connection("default")
    except Exception:
        return None


def _bump_pageview(date, path):
    """Atomically increment the per-path/day page-view counter."""
    from django.db import IntegrityError
    from django.db.models import F
    from src.users.models import PageViewDaily

    updated = PageViewDaily.objects.filter(date=date, path=path).update(
        views=F("views") + 1
    )
    if updated:
        return
    try:
        PageViewDaily.objects.create(date=date, path=path, views=1)
    except IntegrityError:
        # Another worker created the row between our UPDATE and CREATE.
        PageViewDaily.objects.filter(date=date, path=path).update(views=F("views") + 1)


def _bump_unique(date, request, user_agent):
    """Add this visitor to the day's HyperLogLog of approximate uniques.

    The member is a salted BLAKE2 hash of IP + User-Agent. The salt rotates
    daily (the date is part of the hashed input, keyed by SECRET_KEY) and the
    raw hash is never stored — only HLL's fixed-size sketch — so no persistent
    or reversible identifier is retained. Aggregate, cookieless, consent-free.
    """
    conn = _redis()
    if conn is None:
        return
    from src.api.client_ip import get_client_ip

    ip = get_client_ip(request) or "0.0.0.0"
    day = date.isoformat()
    member = hashlib.blake2s(
        f"{ip}|{user_agent}|{day}".encode(),
        key=settings.SECRET_KEY.encode()[:32],
        digest_size=16,
    ).digest()
    key = f"uv:{day}"
    conn.pfadd(key, member)
    conn.expire(key, _UV_TTL_SECONDS)


class TrafficCountingMiddleware:
    """Count real (human) HTML page views without cookies or consent.

    Increments ``users.PageViewDaily`` (durable, per path/day) and a per-day
    Redis HyperLogLog of approximate unique visitors. This is the ground-truth
    visit count that sits next to GA4 (which only sees users who accept the
    cookie banner) and Search Console. Counting never raises into the response.

    Known systematic UNDERCOUNTS (the numbers are a floor, not the full total):
      * Cloudflare full-page cache: requests served from the CF edge (e.g. the
        /blog/ cache rule) never reach Django and so are never counted.
      * HTTP 304 Not Modified: only 200 responses count, so repeat visitors
        whose browser cache is still valid are missed.
      * Redis down: page views still count, but uniques silently read 0.
    Each localized path (/, /ru/, /en/… ) is its own row by design — there is
    no cross-locale aggregation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._count(request, response)
        except Exception:
            logger.debug("TrafficCountingMiddleware: count failed", exc_info=True)
        return response

    def _count(self, request, response):
        if request.method != "GET" or response.status_code != 200:
            return
        if "text/html" not in response.get("Content-Type", ""):
            return
        path = request.path
        if path.startswith(_SKIP_PREFIXES):
            return
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if not user_agent or _BOT_UA_RE.search(user_agent):
            return

        from django.utils import timezone

        today = timezone.now().date()
        _bump_pageview(today, path[:255])
        _bump_unique(today, request, user_agent)


class AnonymousCsrfCookieStripMiddleware:
    """Drop the csrftoken Set-Cookie from anonymous GETs of cacheable pages.

    Tool pages render ``{% csrf_token %}`` (needed by logged-in users, whose
    session-authenticated API calls DO get CSRF-checked), which makes Django
    attach ``Set-Cookie: csrftoken`` to every anonymous page view. Cloudflare
    never caches responses that set cookies, so the "Cache anonymous HTML"
    cache rule was a no-op for exactly the crawler/anon traffic it targets
    (the 2-worker origin melts under parallel crawls — same incident class as
    the /blog/ rule). Anonymous conversion POSTs hit DRF views that are
    csrf-exempt for unauthenticated callers, so the cookie is dead weight for
    them.

    The strip list mirrors the Cloudflare rule's exclusions: pages where an
    anonymous visitor genuinely submits a Django form (login/signup/contact/
    admin) keep the cookie.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        from django.conf import settings

        admin_path = getattr(settings, "ADMIN_URL_PATH", "admin").strip("/")
        self._keep_markers = (
            "/accounts/",
            "/users/",
            "/contact",
            "/api/",
            f"/{admin_path}/",
        )

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method in ("GET", "HEAD")
            and "csrftoken" in response.cookies
            and getattr(request, "user", None) is not None
            and not request.user.is_authenticated
            and not any(m in request.path for m in self._keep_markers)
        ):
            del response.cookies["csrftoken"]
        return response
