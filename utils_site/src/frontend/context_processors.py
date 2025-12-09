"""
Context processors for frontend templates.
"""

import os

from decouple import config
from django.conf import settings
from django.urls import Resolver404, resolve, reverse
from django.utils.translation import get_language


def turnstile_site_key(request):
    """Add Cloudflare Turnstile site key and requirement status to template context."""
    site_key = os.environ.get("TURNSTILE_SITE_KEY", "")
    if not site_key:
        site_key = getattr(settings, "TURNSTILE_SITE_KEY", "")
    if not site_key:
        site_key = config("TURNSTILE_SITE_KEY", default="", cast=str)

    return {
        "turnstile_site_key": site_key,
        "captcha_required": request.session.get("captcha_required", False),
    }


def hreflang_links(request):
    """
    Generate hreflang links for SEO.
    Works with Django's i18n_patterns for proper URL structure.

    Django's i18n_patterns automatically adds language prefix to URLs.
    This function generates proper hreflang tags for all available languages.
    """
    languages = getattr(settings, "LANGUAGES", [("en", "English")])
    default_language = settings.LANGUAGE_CODE

    hreflangs = []
    base_url = f"{request.scheme}://{request.get_host()}"

    # Get current URL pattern name and kwargs
    try:
        match = resolve(request.path)
        url_name = match.url_name
        url_kwargs = match.kwargs
    except (Resolver404, AttributeError):
        url_name = None
        url_kwargs = {}

    # Generate hreflang for each language
    for code, _ in languages:
        try:
            if url_name:
                # Use reverse to get proper URL for each language
                # We need to temporarily activate the language to get correct URL
                from django.utils.translation import activate

                old_lang = get_language()
                activate(code)

                try:
                    # Reverse the URL with the language context
                    lang_url = reverse(url_name, kwargs=url_kwargs)
                    # i18n_patterns adds language prefix automatically
                    # Ensure proper encoding
                    if isinstance(lang_url, bytes):
                        lang_url = lang_url.decode("utf-8")
                    url = f"{base_url}{lang_url}"
                except Exception:
                    # Fallback: construct URL manually
                    current_path = request.path
                    # Ensure current_path is a string, not bytes
                    if isinstance(current_path, bytes):
                        current_path = current_path.decode("utf-8")
                    # Remove current language prefix
                    for lang_code, _ in languages:
                        if current_path.startswith(f"/{lang_code}/"):
                            current_path = current_path.replace(
                                f"/{lang_code}/", "/", 1
                            )
                            break
                        elif current_path == f"/{lang_code}":
                            current_path = "/"
                            break

                    # Add new language prefix
                    if code != default_language:
                        if current_path == "/":
                            lang_path = f"/{code}/"
                        else:
                            lang_path = f"/{code}{current_path}"
                    else:
                        # Default language might not have prefix
                        lang_path = current_path if current_path != "/" else "/"

                    url = f"{base_url}{lang_path}"

                finally:
                    activate(old_lang)
            else:
                # No URL name, construct manually
                current_path = request.path
                # Ensure current_path is a string, not bytes
                if isinstance(current_path, bytes):
                    current_path = current_path.decode("utf-8")
                # Remove current language prefix
                for lang_code, _ in languages:
                    if current_path.startswith(f"/{lang_code}/"):
                        current_path = current_path.replace(f"/{lang_code}/", "/", 1)
                        break
                    elif current_path == f"/{lang_code}":
                        current_path = "/"
                        break

                # Add new language prefix
                if code != default_language:
                    if current_path == "/":
                        lang_path = f"/{code}/"
                    else:
                        lang_path = f"/{code}{current_path}"
                else:
                    lang_path = current_path if current_path != "/" else "/"

                url = f"{base_url}{lang_path}"

        except Exception:
            # Ultimate fallback
            url = f"{base_url}{request.path}?lang={code}"

        hreflangs.append({"code": code, "url": url})

    # Add x-default pointing to default language version
    try:
        if url_name:
            from django.utils.translation import activate

            old_lang = get_language()
            activate(default_language)

            try:
                default_url_path = reverse(url_name, kwargs=url_kwargs)
                # Ensure proper encoding
                if isinstance(default_url_path, bytes):
                    default_url_path = default_url_path.decode("utf-8")
            except Exception:
                default_url_path = request.path
                # Ensure default_url_path is a string, not bytes
                if isinstance(default_url_path, bytes):
                    default_url_path = default_url_path.decode("utf-8")
                # Remove any language prefix for default language
                for lang_code, _ in languages:
                    if default_url_path.startswith(f"/{lang_code}/"):
                        default_url_path = default_url_path.replace(
                            f"/{lang_code}/", "/", 1
                        )
                        break
                    elif default_url_path == f"/{lang_code}":
                        default_url_path = "/"
                        break
            finally:
                activate(old_lang)
        else:
            default_url_path = request.path
            # Ensure default_url_path is a string, not bytes
            if isinstance(default_url_path, bytes):
                default_url_path = default_url_path.decode("utf-8")
            # Remove any language prefix for default language
            for lang_code, _ in languages:
                if default_url_path.startswith(f"/{lang_code}/"):
                    default_url_path = default_url_path.replace(
                        f"/{lang_code}/", "/", 1
                    )
                    break
                elif default_url_path == f"/{lang_code}":
                    default_url_path = "/"
                    break

        default_url = f"{base_url}{default_url_path}"
    except Exception:
        default_url = f"{base_url}{request.path}"

    hreflangs.append({"code": "x-default", "url": default_url})

    return {"hreflangs": hreflangs}
