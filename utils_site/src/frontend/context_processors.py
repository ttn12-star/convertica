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
    """Generate breadcrumbs for BreadcrumbList Schema and visual display."""
    from django.utils.translation import gettext as _

    breadcrumbs_list = [{"name": _("Home"), "url": "/"}]

    # Get current path
    path = request.path.strip("/")
    if not path:
        return {
            "breadcrumbs_schema": breadcrumbs_list,
            "breadcrumb_items": breadcrumbs_list,
        }

    # Try to resolve URL to get view name
    try:
        resolved = resolve(request.path)
        view_name = resolved.view_name

        # Map view names to breadcrumb names (translatable)
        breadcrumb_names = {
            # PDF Conversion
            "frontend:pdf_to_word_page": _("PDF to Word"),
            "frontend:word_to_pdf_page": _("Word to PDF"),
            "frontend:pdf_to_jpg_page": _("PDF to JPG"),
            "frontend:jpg_to_pdf_page": _("JPG to PDF"),
            "frontend:pdf_to_excel_page": _("PDF to Excel"),
            "frontend:excel_to_pdf_page": _("Excel to PDF"),
            "frontend:ppt_to_pdf_page": _("PowerPoint to PDF"),
            "frontend:pdf_to_ppt_page": _("PDF to PowerPoint"),
            "frontend:html_to_pdf_page": _("HTML to PDF"),
            "frontend:pdf_to_html_page": _("PDF to HTML"),
            # PDF Edit
            "frontend:rotate_pdf_page": _("Rotate PDF"),
            "frontend:add_page_numbers_page": _("Add Page Numbers"),
            "frontend:add_watermark_page": _("Add Watermark"),
            "frontend:crop_pdf_page": _("Crop PDF"),
            # PDF Organize
            "frontend:merge_pdf_page": _("Merge PDF"),
            "frontend:split_pdf_page": _("Split PDF"),
            "frontend:remove_pages_page": _("Remove Pages"),
            "frontend:extract_pages_page": _("Extract Pages"),
            "frontend:organize_pdf_page": _("Organize PDF"),
            "frontend:compress_pdf_page": _("Compress PDF"),
            # PDF Security
            "frontend:protect_pdf_page": _("Protect PDF"),
            "frontend:unlock_pdf_page": _("Unlock PDF"),
            # Static pages
            "frontend:all_tools_page": _("All Tools"),
            "frontend:pricing": _("Pricing"),
            "frontend:about_page": _("About"),
            "frontend:faq_page": _("FAQ"),
            "frontend:contact_page": _("Contact"),
            "frontend:privacy_page": _("Privacy Policy"),
            "frontend:terms_page": _("Terms of Service"),
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

    # Add position to each breadcrumb for visual display
    breadcrumb_items = []
    for idx, crumb in enumerate(breadcrumbs_list, start=1):
        breadcrumb_items.append(
            {"name": crumb["name"], "url": crumb["url"], "position": idx}
        )

    return {
        "breadcrumbs_schema": breadcrumbs_list,
        "breadcrumb_items": breadcrumb_items,
    }


def related_tools(request):
    """Generate related tools suggestions based on current page."""
    from django.urls import reverse
    from django.utils.translation import gettext as _

    # Define tool relationships for cross-promotion
    tools_map = {
        "pdf_to_word": ["word_to_pdf", "pdf_to_excel", "pdf_to_ppt"],
        "word_to_pdf": ["pdf_to_word", "excel_to_pdf", "ppt_to_pdf"],
        "pdf_to_jpg": ["jpg_to_pdf", "pdf_to_word", "compress_pdf"],
        "jpg_to_pdf": ["pdf_to_jpg", "merge_pdf", "compress_pdf"],
        "pdf_to_excel": ["excel_to_pdf", "pdf_to_word", "pdf_to_ppt"],
        "excel_to_pdf": ["pdf_to_excel", "word_to_pdf", "ppt_to_pdf"],
        "pdf_to_ppt": ["ppt_to_pdf", "pdf_to_word", "pdf_to_excel"],
        "ppt_to_pdf": ["pdf_to_ppt", "word_to_pdf", "excel_to_pdf"],
        "pdf_to_html": ["html_to_pdf", "pdf_to_word", "pdf_to_excel"],
        "html_to_pdf": ["pdf_to_html", "word_to_pdf", "merge_pdf"],
        "merge_pdf": ["split_pdf", "organize_pdf", "compress_pdf"],
        "split_pdf": ["merge_pdf", "extract_pages", "remove_pages"],
        "compress_pdf": ["pdf_to_jpg", "merge_pdf", "rotate_pdf"],
        "extract_pages": ["remove_pages", "split_pdf", "organize_pdf"],
        "remove_pages": ["extract_pages", "split_pdf", "organize_pdf"],
        "organize_pdf": ["merge_pdf", "split_pdf", "extract_pages"],
        "rotate_pdf": ["crop_pdf", "add_watermark", "add_page_numbers"],
        "crop_pdf": ["rotate_pdf", "add_watermark", "compress_pdf"],
        "add_watermark": ["add_page_numbers", "rotate_pdf", "protect_pdf"],
        "add_page_numbers": ["add_watermark", "rotate_pdf", "organize_pdf"],
        "protect_pdf": ["unlock_pdf", "add_watermark", "compress_pdf"],
        "unlock_pdf": ["protect_pdf", "merge_pdf", "split_pdf"],
    }

    # Tool metadata - icons and colors match header.html menu
    tools_info = {
        "pdf_to_word": {
            "name": _("PDF to Word"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "description": _("Convert PDF to Word"),
        },
        "word_to_pdf": {
            "name": _("Word to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "description": _("Convert Word to PDF"),
        },
        "pdf_to_jpg": {
            "name": _("PDF to JPG"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
            "gradient": "from-rose-500 to-rose-600",
            "description": _("Convert PDF to JPG"),
        },
        "jpg_to_pdf": {
            "name": _("JPG to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-pink-500 to-pink-600",
            "description": _("Convert JPG to PDF"),
        },
        "pdf_to_excel": {
            "name": _("PDF to Excel"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
            "gradient": "from-emerald-500 to-emerald-600",
            "description": _("Convert PDF to Excel"),
        },
        "excel_to_pdf": {
            "name": _("Excel to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5h16v14H4V5zm4 0v14M4 9h16M4 13h16"/>',
            "gradient": "from-green-500 to-green-600",
            "description": _("Convert Excel to PDF"),
        },
        "merge_pdf": {
            "name": _("Merge PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>',
            "gradient": "from-green-500 to-green-600",
            "description": _("Merge multiple PDFs"),
        },
        "split_pdf": {
            "name": _("Split PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-blue-500 to-blue-600",
            "description": _("Split PDF into parts"),
        },
        "compress_pdf": {
            "name": _("Compress PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>',
            "gradient": "from-orange-500 to-orange-600",
            "description": _("Reduce PDF size"),
        },
        "rotate_pdf": {
            "name": _("Rotate PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
            "gradient": "from-purple-500 to-purple-600",
            "description": _("Rotate PDF pages"),
        },
        "protect_pdf": {
            "name": _("Protect PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-red-500 to-red-600",
            "description": _("Password protect PDF"),
        },
        "unlock_pdf": {
            "name": _("Unlock PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
            "gradient": "from-green-500 to-green-600",
            "description": _("Remove PDF password"),
        },
        "organize_pdf": {
            "name": _("Organize PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"/>',
            "gradient": "from-teal-500 to-teal-600",
            "description": _("Reorder PDF pages"),
        },
        "extract_pages": {
            "name": _("Extract Pages"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-yellow-500 to-yellow-600",
            "description": _("Extract specific pages"),
        },
        "remove_pages": {
            "name": _("Remove Pages"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
            "gradient": "from-red-500 to-red-600",
            "description": _("Remove pages from PDF"),
        },
        "crop_pdf": {
            "name": _("Crop PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>',
            "gradient": "from-green-500 to-green-600",
            "description": _("Crop PDF pages"),
        },
        "add_watermark": {
            "name": _("Add Watermark"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-pink-500 to-pink-600",
            "description": _("Add watermark to PDF"),
        },
        "add_page_numbers": {
            "name": _("Add Page Numbers"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>',
            "gradient": "from-blue-500 to-blue-600",
            "description": _("Number PDF pages"),
        },
        "ppt_to_pdf": {
            "name": _("PowerPoint to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4h16v10H4V4zm6 16h4m-2-6v6"/>',
            "gradient": "from-orange-500 to-orange-600",
            "description": _("Convert PowerPoint to PDF"),
        },
        "pdf_to_ppt": {
            "name": _("PDF to PowerPoint"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4h16v10H4V4zm6 16h4m-2-6v6"/>',
            "gradient": "from-amber-500 to-amber-600",
            "description": _("Convert PDF to PowerPoint"),
        },
        "html_to_pdf": {
            "name": _("HTML to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "description": _("Convert HTML to PDF"),
        },
        "pdf_to_html": {
            "name": _("PDF to HTML"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
            "gradient": "from-teal-500 to-teal-600",
            "description": _("Convert PDF to HTML"),
        },
    }

    # Try to determine current tool from URL
    try:
        resolved = resolve(request.path)
        view_name = resolved.view_name

        # Extract tool name from view name
        current_tool = None
        for tool_key in tools_map.keys():
            if tool_key in view_name:
                current_tool = tool_key
                break

        # Get related tools
        related_list = []
        if current_tool and current_tool in tools_map:
            for tool_key in tools_map[current_tool][:3]:  # Limit to 3 related tools
                if tool_key in tools_info:
                    tool = tools_info[tool_key]
                    try:
                        url = reverse(f"frontend:{tool_key}_page")
                        related_list.append(
                            {
                                "name": tool["name"],
                                "url": url,
                                "icon": tool["icon"],
                                "gradient": tool["gradient"],
                                "description": tool["description"],
                            }
                        )
                    except Exception:
                        continue

        return {"related_tools": related_list}
    except Exception:
        return {"related_tools": []}
