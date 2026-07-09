"""
Custom i18n views to prevent double language prefixes in URLs.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate, check_for_language


def remove_all_language_prefixes(path):
    """
    Remove ALL language prefixes from URL path.
    Used to prevent double language prefixes in URLs.
    """
    if not path:
        return path

    parsed = urlsplit(str(path))
    path = parsed.path.lstrip("/")
    languages = getattr(settings, "LANGUAGES", [])
    supported_codes = [code for code, _ in languages]

    # Remove ALL language prefixes
    removed_any = True
    while removed_any:
        removed_any = False
        for lang_code in supported_codes:
            if path.startswith(f"{lang_code}/"):
                path = path[len(lang_code) + 1 :]
                removed_any = True
                break
            elif path == lang_code:
                path = ""
                removed_any = True
                break

    cleaned_path = "/" + path if path else "/"
    if parsed.query:
        cleaned_path = f"{cleaned_path}?{parsed.query}"
    if parsed.fragment:
        cleaned_path = f"{cleaned_path}#{parsed.fragment}"
    return cleaned_path


def _build_allowed_hosts(request) -> set[str]:
    """Build allowed hosts for safe redirect validation without raising DisallowedHost."""
    allowed_hosts = set(getattr(settings, "ALLOWED_HOSTS", []) or [])
    try:
        allowed_hosts.add(request.get_host())
    except DisallowedHost:
        # Invalid request host should not break language switching for relative URLs.
        pass
    return allowed_hosts


def _resolve_next_url(request) -> str:
    """Resolve a safe internal URL to redirect after language switch."""
    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.META.get("HTTP_REFERER")
        or "/"
    )
    next_url = remove_all_language_prefixes(next_url)

    allowed_hosts = _build_allowed_hosts(request)
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return "/"

    return next_url


def set_language_cookie(response, lang_code):
    """Persist the chosen language in the LocaleMiddleware cookie.

    LocaleMiddleware checks this cookie before the Accept-Language header, so
    setting it makes the choice stick on the next visit — including a fresh
    device, when we replay a logged-in user's stored preference on login.
    """
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang_code,
        max_age=getattr(settings, "LANGUAGE_COOKIE_AGE", 365 * 24 * 60 * 60),
        path=getattr(settings, "LANGUAGE_COOKIE_PATH", "/"),
        domain=getattr(settings, "LANGUAGE_COOKIE_DOMAIN", None),
        secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
        httponly=getattr(settings, "LANGUAGE_COOKIE_HTTPONLY", False),
        samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Lax"),
    )
    return response


def set_language(request):
    """
    Custom set_language view that prevents double language prefixes.

    This is a wrapper around Django's set_language that ensures
    the 'next' parameter doesn't contain language prefixes before redirect.
    This prevents URLs like /en/pl/... from being created.
    """
    next_url = _resolve_next_url(request)
    lang_code = request.POST.get("language") or request.GET.get("language")
    supported_languages = dict(getattr(settings, "LANGUAGES", []))

    if lang_code and lang_code in supported_languages and check_for_language(lang_code):
        # Store in session if available.
        if hasattr(request, "session"):
            request.session["django_language"] = lang_code

        activate(lang_code)

        # Remember an explicit choice on the account so we can restore it on a
        # different device at login (the cookie alone doesn't travel).
        user = getattr(request, "user", None)
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and user.preferred_language != lang_code
        ):
            user.preferred_language = lang_code
            user.save(update_fields=["preferred_language"])

        # For default language keep URL without language prefix.
        if lang_code == settings.LANGUAGE_CODE:
            final_url = next_url
        else:
            final_url = (
                f"/{lang_code}/" if next_url == "/" else f"/{lang_code}{next_url}"
            )

        response = HttpResponseRedirect(final_url)
        return set_language_cookie(response, lang_code)

    # Always redirect away from setlang endpoint, even if language is missing/invalid.
    return HttpResponseRedirect(next_url)
