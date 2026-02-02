"""
Custom i18n views to prevent double language prefixes in URLs.
"""

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate
from django.views.i18n import set_language as django_set_language


def remove_all_language_prefixes(path):
    """
    Remove ALL language prefixes from URL path.
    Used to prevent double language prefixes in URLs.
    """
    if not path:
        return path

    path = str(path).lstrip("/")
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

    return "/" + path if path else "/"


def set_language(request):
    """
    Custom set_language view that prevents double language prefixes.

    This is a wrapper around Django's set_language that ensures
    the 'next' parameter doesn't contain language prefixes before redirect.
    This prevents URLs like /en/pl/... from being created.
    """
    if request.method == "POST":
        lang_code = request.POST.get("language")
        if lang_code and lang_code in dict(settings.LANGUAGES):
            # Store in session if available
            if hasattr(request, "session"):
                request.session["django_language"] = lang_code

            activate(lang_code)

            # Get next URL and remove ALL language prefixes from it
            next_url = request.POST.get("next", request.GET.get("next"))
            if not next_url:
                next_url = "/"

            # Remove all language prefixes to prevent double prefixes
            # This is the key fix - even if remove_language_prefix filter
            # didn't work correctly before, we ensure it here
            next_url = remove_all_language_prefixes(next_url)

            # Validate next URL
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                # Add language prefix manually to ensure correct behavior
                # For default language, no prefix is needed (Django i18n_patterns behavior)
                # For other languages, add prefix: /pl/... instead of /en/pl/...
                if lang_code == settings.LANGUAGE_CODE:
                    # Default language - no prefix needed
                    final_url = next_url
                else:
                    # Other languages - add prefix
                    if next_url == "/":
                        final_url = f"/{lang_code}/"
                    else:
                        final_url = f"/{lang_code}{next_url}"

                response = HttpResponseRedirect(final_url)

                # IMPORTANT: Always set the language cookie!
                # LocaleMiddleware checks cookie BEFORE Accept-Language header.
                # Without this cookie, users with browser language set to Russian
                # would be redirected to Russian even after selecting English.
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    lang_code,
                    max_age=(
                        settings.LANGUAGE_COOKIE_AGE
                        if hasattr(settings, "LANGUAGE_COOKIE_AGE")
                        else 365 * 24 * 60 * 60
                    ),  # 1 year default
                    path=(
                        settings.LANGUAGE_COOKIE_PATH
                        if hasattr(settings, "LANGUAGE_COOKIE_PATH")
                        else "/"
                    ),
                    domain=(
                        settings.LANGUAGE_COOKIE_DOMAIN
                        if hasattr(settings, "LANGUAGE_COOKIE_DOMAIN")
                        else None
                    ),
                    secure=(
                        settings.LANGUAGE_COOKIE_SECURE
                        if hasattr(settings, "LANGUAGE_COOKIE_SECURE")
                        else False
                    ),
                    httponly=(
                        settings.LANGUAGE_COOKIE_HTTPONLY
                        if hasattr(settings, "LANGUAGE_COOKIE_HTTPONLY")
                        else False
                    ),
                    samesite=(
                        settings.LANGUAGE_COOKIE_SAMESITE
                        if hasattr(settings, "LANGUAGE_COOKIE_SAMESITE")
                        else "Lax"
                    ),
                )
                return response

    # Fallback to default Django behavior
    return django_set_language(request)
