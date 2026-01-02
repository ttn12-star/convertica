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
    # Skip CAPTCHA in DEBUG mode
    if settings.DEBUG:
        return {
            "turnstile_site_key": "",
            "captcha_required": False,
        }

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
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"
    site_domain = config("SITE_DOMAIN", default=None)
    base_url = f"{scheme}://{site_domain or request.get_host()}"

    # Get current URL pattern name and kwargs
    try:
        match = resolve(request.path)
        url_name = match.url_name
        url_kwargs = match.kwargs
    except (Resolver404, AttributeError):
        url_name = None
        url_kwargs = {}

    homepage_paths = [f"/{code}/" for code, _ in languages]
    if request.path == "/" or request.path in homepage_paths:
        hreflangs = []
        for code, _ in languages:
            if code == default_language:
                url = f"{base_url}/"
            else:
                url = f"{base_url}/{code}/"
            hreflangs.append({"code": code, "url": url})
        hreflangs.append({"code": "x-default", "url": f"{base_url}/"})
        return {
            "hreflangs": hreflangs,
            "hreflang_homepage_paths": homepage_paths,
            "default_language_code": default_language,
        }

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
                        # Django i18n_patterns adds prefix for ALL languages, including default
                        if current_path == "/":
                            lang_path = f"/{code}/"
                        else:
                            lang_path = f"/{code}{current_path}"

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
                    # Django i18n_patterns adds prefix for ALL languages, including default
                    if current_path == "/":
                        lang_path = f"/{code}/"
                    else:
                        lang_path = f"/{code}{current_path}"

                url = f"{base_url}{lang_path}"

        except Exception:
            # Skip this language if we can't generate a proper URL
            # Don't create URLs with ?lang= parameter as they create duplicates
            continue

        hreflangs.append({"code": code, "url": url})

    # Add x-default pointing to root for homepage, default language for other pages
    try:
        # For homepage, x-default should point to root (/)
        languages = getattr(settings, "LANGUAGES", [("en", "English")])
        homepage_paths = [f"/{code}/" for code, _ in languages]

        if request.path == "/" or request.path in homepage_paths:
            default_url = f"{base_url}/"
        else:
            # For other pages, point to default language version
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
                finally:
                    activate(old_lang)
            else:
                default_url_path = request.path
                # Ensure default_url_path is a string, not bytes
                if isinstance(default_url_path, bytes):
                    default_url_path = default_url_path.decode("utf-8")

            default_url = f"{base_url}{default_url_path}"
    except Exception:
        default_url = f"{base_url}{request.path}"

    hreflangs.append({"code": "x-default", "url": default_url})

    # Also return list of homepage paths for canonical URL logic
    languages = getattr(settings, "LANGUAGES", [("en", "English")])
    homepage_paths = [f"/{code}/" for code, _ in languages]

    return {
        "hreflangs": hreflangs,
        "hreflang_homepage_paths": homepage_paths,
        "default_language_code": default_language,
    }


def site_urls(request):
    """Generate site base URL and current URL for templates."""
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    site_domain = config("SITE_DOMAIN", default=None)
    base_url = f"{scheme}://{site_domain or request.get_host()}"
    return {
        "site_base_url": base_url,
        "site_current_url": f"{base_url}{request.path}",
    }


def site_settings(request):
    """Add site-wide settings to template context."""
    from django.conf import settings

    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Convertica"),
        "SITE_URL": getattr(settings, "SITE_URL", "https://convertica.net"),
        "VAPID_PUBLIC_KEY": getattr(settings, "VAPID_PUBLIC_KEY", ""),
    }


def js_settings(request):
    """Add configurable JS settings to template context.

    These settings are passed to JavaScript via window object.
    """
    return {
        "js_settings": {
            # Time in seconds before showing patience message during long conversions
            "patience_message_delay": getattr(settings, "PATIENCE_MESSAGE_DELAY", 40),
            # Polling interval for async tasks (milliseconds)
            "poll_interval": getattr(settings, "ASYNC_POLL_INTERVAL", 2500),
        }
    }


def conversion_limits(request):
    try:
        from src.api import conversion_limits as api_limits
    except Exception:
        api_limits = None

    max_free_pdf_pages = getattr(settings, "MAX_FREE_PDF_PAGES", None)
    if max_free_pdf_pages is None:
        max_free_pdf_pages = getattr(settings, "MAX_PDF_PAGES", None)

    if max_free_pdf_pages is None and api_limits is not None:
        max_free_pdf_pages = getattr(api_limits, "MAX_PDF_PAGES", 30)
    if max_free_pdf_pages is None:
        max_free_pdf_pages = 30

    max_free_pdf_pages_heavy = getattr(settings, "MAX_FREE_PDF_PAGES_HEAVY", None)
    if max_free_pdf_pages_heavy is None:
        max_free_pdf_pages_heavy = getattr(settings, "MAX_PDF_PAGES_HEAVY", None)
    if max_free_pdf_pages_heavy is None and api_limits is not None:
        max_free_pdf_pages_heavy = getattr(
            api_limits, "MAX_PDF_PAGES_HEAVY", max_free_pdf_pages
        )
    if max_free_pdf_pages_heavy is None:
        max_free_pdf_pages_heavy = max_free_pdf_pages

    max_file_size = getattr(settings, "MAX_FILE_SIZE", None)
    if max_file_size is None and api_limits is not None:
        max_file_size = getattr(api_limits, "MAX_FILE_SIZE", 25 * 1024 * 1024)
    if max_file_size is None:
        max_file_size = 25 * 1024 * 1024

    max_file_size_premium = getattr(settings, "MAX_FILE_SIZE_PREMIUM", None)
    if max_file_size_premium is None and api_limits is not None:
        max_file_size_premium = getattr(
            api_limits, "MAX_FILE_SIZE_PREMIUM", 200 * 1024 * 1024
        )
    if max_file_size_premium is None:
        max_file_size_premium = 200 * 1024 * 1024

    return {
        "conversion_limits": {
            "max_free_pdf_pages": int(max_free_pdf_pages),
            "max_free_pdf_pages_heavy": int(max_free_pdf_pages_heavy),
            "max_file_size": int(max_file_size),
            "max_file_size_premium": int(max_file_size_premium),
        }
    }


def payments_enabled(request):
    """Add PAYMENTS_ENABLED flag to context."""
    return {"PAYMENTS_ENABLED": getattr(settings, "PAYMENTS_ENABLED", True)}


def breadcrumbs(request):
    """Generate breadcrumbs for BreadcrumbList Schema."""
    breadcrumbs_list = [{"name": "Home", "url": "/"}]

    # Get current path
    path = request.path.strip("/")
    if not path:
        return {"breadcrumbs_schema": breadcrumbs_list}

    # Try to resolve URL to get view name
    try:
        resolved = resolve(request.path)
        view_name = resolved.view_name

        # Map view names to breadcrumb names
        breadcrumb_names = {
            # PDF Conversion
            "frontend:pdf_to_word_page": "PDF to Word",
            "frontend:word_to_pdf_page": "Word to PDF",
            "frontend:pdf_to_jpg_page": "PDF to JPG",
            "frontend:jpg_to_pdf_page": "JPG to PDF",
            "frontend:pdf_to_excel_page": "PDF to Excel",
            "frontend:excel_to_pdf_page": "Excel to PDF",
            "frontend:ppt_to_pdf_page": "PowerPoint to PDF",
            "frontend:pdf_to_ppt_page": "PDF to PowerPoint",
            "frontend:html_to_pdf_page": "HTML to PDF",
            "frontend:pdf_to_html_page": "PDF to HTML",
            # PDF Edit
            "frontend:rotate_pdf_page": "Rotate PDF",
            "frontend:add_page_numbers_page": "Add Page Numbers",
            "frontend:add_watermark_page": "Add Watermark",
            "frontend:crop_pdf_page": "Crop PDF",
            # PDF Organize
            "frontend:merge_pdf_page": "Merge PDF",
            "frontend:split_pdf_page": "Split PDF",
            "frontend:remove_pages_page": "Remove Pages",
            "frontend:extract_pages_page": "Extract Pages",
            "frontend:organize_pdf_page": "Organize PDF",
            "frontend:compress_pdf_page": "Compress PDF",
            # PDF Security
            "frontend:protect_pdf_page": "Protect PDF",
            "frontend:unlock_pdf_page": "Unlock PDF",
            # Static pages
            "frontend:all_tools_page": "All Tools",
            "frontend:pricing": "Pricing",
            "frontend:about_page": "About",
            "frontend:faq_page": "FAQ",
            "frontend:contact_page": "Contact",
            "frontend:privacy_page": "Privacy Policy",
            "frontend:terms_page": "Terms of Service",
        }

        if view_name in breadcrumb_names:
            breadcrumbs_list.append(
                {"name": breadcrumb_names[view_name], "url": request.path}
            )
        else:
            # Fallback: use path segments
            parts = path.split("/")
            current_path = ""
            for part in parts:
                if part:
                    current_path += f"/{part}"
                    name = part.replace("-", " ").title()
                    breadcrumbs_list.append({"name": name, "url": current_path})
    except Resolver404:
        # Fallback for unresolved URLs
        parts = path.split("/")
        current_path = ""
        for part in parts:
            if part:
                current_path += f"/{part}"
                name = part.replace("-", " ").title()
                breadcrumbs_list.append({"name": name, "url": current_path})

    return {"breadcrumbs_schema": breadcrumbs_list}
