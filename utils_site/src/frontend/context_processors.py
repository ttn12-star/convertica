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
            # Ultimate fallback
            url = f"{base_url}{request.path}?lang={code}"

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


def payments_enabled(request):
    return {"PAYMENTS_ENABLED": bool(getattr(settings, "PAYMENTS_ENABLED", True))}


def site_urls(request):
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    site_domain = config("SITE_DOMAIN", default=None)
    base_url = f"{scheme}://{site_domain or request.get_host()}"
    return {
        "site_base_url": base_url,
        "site_current_url": f"{base_url}{request.path}",
    }


def breadcrumbs(request):
    """
    Generate breadcrumb navigation for SEO and user experience.
    Returns breadcrumb items for both display and Schema.org BreadcrumbList.
    """
    from django.utils.translation import gettext as _

    breadcrumb_items = []
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    site_domain = config("SITE_DOMAIN", default=None)
    base_url = f"{scheme}://{site_domain or request.get_host()}"

    # Always add Home as first item
    breadcrumb_items.append({"name": _("Home"), "url": f"{base_url}/", "position": 1})

    # Get current path and parse it
    path = request.path.strip("/")
    if not path:
        # Homepage - only Home breadcrumb
        return {"breadcrumb_items": breadcrumb_items}

    # Remove language prefix if present
    language_code = get_language()
    if path.startswith(f"{language_code}/"):
        path = path[len(language_code) + 1 :]

    # Define breadcrumb mappings for different sections
    breadcrumb_map = {
        # Converters
        "pdf-to-word": _("PDF to Word"),
        "word-to-pdf": _("Word to PDF"),
        "pdf-to-jpg": _("PDF to JPG"),
        "jpg-to-pdf": _("JPG to PDF"),
        "pdf-to-excel": _("PDF to Excel"),
        "excel-to-pdf": _("Excel to PDF"),
        "pdf-to-ppt": _("PDF to PowerPoint"),
        "ppt-to-pdf": _("PowerPoint to PDF"),
        "pdf-to-html": _("PDF to HTML"),
        "html-to-pdf": _("HTML to PDF"),
        # PDF Edit
        "pdf-edit": _("PDF Edit"),
        "rotate": _("Rotate PDF"),
        "crop": _("Crop PDF"),
        "add-watermark": _("Add Watermark"),
        "add-page-numbers": _("Add Page Numbers"),
        # PDF Organize
        "pdf-organize": _("PDF Organize"),
        "merge": _("Merge PDF"),
        "split": _("Split PDF"),
        "compress": _("Compress PDF"),
        "extract-pages": _("Extract Pages"),
        "remove-pages": _("Remove Pages"),
        "organize": _("Organize PDF"),
        # PDF Security
        "pdf-security": _("PDF Security"),
        "protect": _("Protect PDF"),
        "unlock": _("Unlock PDF"),
        # Other pages
        "blog": _("Blog"),
        "about": _("About"),
        "contact": _("Contact"),
        "faq": _("FAQ"),
        "privacy": _("Privacy Policy"),
        "terms": _("Terms of Service"),
        "all-tools": _("All Tools"),
    }

    # Parse path segments
    segments = path.split("/")
    current_path = ""
    position = 2

    for segment in segments:
        if not segment:
            continue

        current_path += f"/{segment}"

        # Get breadcrumb name
        if segment in breadcrumb_map:
            name = breadcrumb_map[segment]
        else:
            # Fallback: capitalize and replace hyphens
            name = segment.replace("-", " ").title()

        # Build URL
        if language_code and language_code != settings.LANGUAGE_CODE:
            url = f"{base_url}/{language_code}{current_path}"
        else:
            url = f"{base_url}{current_path}"

        breadcrumb_items.append({"name": name, "url": url, "position": position})
        position += 1

    return {"breadcrumb_items": breadcrumb_items}


def related_tools(request):
    """
    Generate related tools suggestions based on current page.
    Returns list of related tools for cross-promotion and internal linking.
    """
    from django.urls import reverse
    from django.utils.translation import gettext as _

    # Define tool relationships
    tools_map = {
        "pdf_to_word": [
            "word_to_pdf",
            "pdf_to_excel",
            "pdf_to_ppt",
            "pdf_to_html",
            "pdf_to_jpg",
        ],
        "word_to_pdf": ["pdf_to_word", "excel_to_pdf", "ppt_to_pdf", "html_to_pdf"],
        "pdf_to_jpg": ["jpg_to_pdf", "pdf_to_word", "pdf_to_excel", "compress_pdf"],
        "jpg_to_pdf": ["pdf_to_jpg", "merge_pdf", "compress_pdf"],
        "pdf_to_excel": ["excel_to_pdf", "pdf_to_word", "pdf_to_ppt"],
        "excel_to_pdf": ["pdf_to_excel", "word_to_pdf", "ppt_to_pdf"],
        "pdf_to_ppt": ["ppt_to_pdf", "pdf_to_word", "pdf_to_excel"],
        "ppt_to_pdf": ["pdf_to_ppt", "word_to_pdf", "excel_to_pdf"],
        "pdf_to_html": ["html_to_pdf", "pdf_to_word", "pdf_to_excel"],
        "html_to_pdf": ["pdf_to_html", "word_to_pdf", "merge_pdf"],
        "merge_pdf": ["split_pdf", "organize_pdf", "compress_pdf"],
        "split_pdf": ["merge_pdf", "extract_pages", "remove_pages"],
        "compress_pdf": ["merge_pdf", "split_pdf", "pdf_to_jpg"],
        "extract_pages": ["remove_pages", "split_pdf", "organize_pdf"],
        "remove_pages": ["extract_pages", "split_pdf", "organize_pdf"],
        "organize_pdf": ["merge_pdf", "split_pdf", "extract_pages"],
        "rotate_pdf": ["crop_pdf", "organize_pdf", "merge_pdf"],
        "crop_pdf": ["rotate_pdf", "add_watermark", "compress_pdf"],
        "add_watermark": ["crop_pdf", "add_page_numbers", "protect_pdf"],
        "add_page_numbers": ["add_watermark", "organize_pdf", "merge_pdf"],
        "protect_pdf": ["unlock_pdf", "add_watermark", "compress_pdf"],
        "unlock_pdf": ["protect_pdf", "merge_pdf", "split_pdf"],
    }

    # Tool metadata
    tools_info = {
        "pdf_to_word": {
            "name": _("PDF to Word"),
            "description": _("Convert PDF to editable Word documents"),
            "url_name": "pdf_to_word_page",
            "gradient": "from-blue-500 to-blue-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
        },
        "word_to_pdf": {
            "name": _("Word to PDF"),
            "description": _("Convert Word documents to PDF format"),
            "url_name": "word_to_pdf_page",
            "gradient": "from-indigo-500 to-indigo-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
        },
        "pdf_to_jpg": {
            "name": _("PDF to JPG"),
            "description": _("Convert PDF pages to JPG images"),
            "url_name": "pdf_to_jpg_page",
            "gradient": "from-green-500 to-green-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
        },
        "jpg_to_pdf": {
            "name": _("JPG to PDF"),
            "description": _("Convert images to PDF documents"),
            "url_name": "jpg_to_pdf_page",
            "gradient": "from-emerald-500 to-emerald-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
        },
        "pdf_to_excel": {
            "name": _("PDF to Excel"),
            "description": _("Extract tables from PDF to Excel"),
            "url_name": "pdf_to_excel_page",
            "gradient": "from-teal-500 to-teal-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
        },
        "excel_to_pdf": {
            "name": _("Excel to PDF"),
            "description": _("Convert Excel spreadsheets to PDF"),
            "url_name": "excel_to_pdf_page",
            "gradient": "from-cyan-500 to-cyan-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/>',
        },
        "pdf_to_ppt": {
            "name": _("PDF to PowerPoint"),
            "description": _("Convert PDF to editable presentations"),
            "url_name": "pdf_to_ppt_page",
            "gradient": "from-orange-500 to-orange-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
        },
        "ppt_to_pdf": {
            "name": _("PowerPoint to PDF"),
            "description": _("Convert presentations to PDF format"),
            "url_name": "ppt_to_pdf_page",
            "gradient": "from-red-500 to-red-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
        },
        "pdf_to_html": {
            "name": _("PDF to HTML"),
            "description": _("Convert PDF to HTML web pages"),
            "url_name": "pdf_to_html_page",
            "gradient": "from-purple-500 to-purple-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
        },
        "html_to_pdf": {
            "name": _("HTML to PDF"),
            "description": _("Convert web pages to PDF documents"),
            "url_name": "html_to_pdf_page",
            "gradient": "from-pink-500 to-pink-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
        },
        "merge_pdf": {
            "name": _("Merge PDF"),
            "description": _("Combine multiple PDFs into one"),
            "url_name": "merge_pdf_page",
            "gradient": "from-violet-500 to-violet-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
        },
        "split_pdf": {
            "name": _("Split PDF"),
            "description": _("Split PDF into separate pages"),
            "url_name": "split_pdf_page",
            "gradient": "from-fuchsia-500 to-fuchsia-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/>',
        },
        "compress_pdf": {
            "name": _("Compress PDF"),
            "description": _("Reduce PDF file size"),
            "url_name": "compress_pdf_page",
            "gradient": "from-amber-500 to-amber-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>',
        },
        "extract_pages": {
            "name": _("Extract Pages"),
            "description": _("Extract specific pages from PDF"),
            "url_name": "extract_pages_page",
            "gradient": "from-lime-500 to-lime-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
        },
        "remove_pages": {
            "name": _("Remove Pages"),
            "description": _("Delete unwanted pages from PDF"),
            "url_name": "remove_pages_page",
            "gradient": "from-rose-500 to-rose-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
        },
        "organize_pdf": {
            "name": _("Organize PDF"),
            "description": _("Reorder and arrange PDF pages"),
            "url_name": "organize_pdf_page",
            "gradient": "from-sky-500 to-sky-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>',
        },
        "rotate_pdf": {
            "name": _("Rotate PDF"),
            "description": _("Rotate PDF pages to correct orientation"),
            "url_name": "rotate_pdf_page",
            "gradient": "from-blue-500 to-blue-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
        },
        "crop_pdf": {
            "name": _("Crop PDF"),
            "description": _("Trim and crop PDF pages"),
            "url_name": "crop_pdf_page",
            "gradient": "from-indigo-500 to-indigo-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z"/>',
        },
        "add_watermark": {
            "name": _("Add Watermark"),
            "description": _("Add text or image watermark to PDF"),
            "url_name": "add_watermark_page",
            "gradient": "from-purple-500 to-purple-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
        },
        "add_page_numbers": {
            "name": _("Add Page Numbers"),
            "description": _("Add page numbers to PDF documents"),
            "url_name": "add_page_numbers_page",
            "gradient": "from-teal-500 to-teal-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>',
        },
        "protect_pdf": {
            "name": _("Protect PDF"),
            "description": _("Add password protection to PDF"),
            "url_name": "protect_pdf_page",
            "gradient": "from-red-500 to-red-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
        },
        "unlock_pdf": {
            "name": _("Unlock PDF"),
            "description": _("Remove password from PDF"),
            "url_name": "unlock_pdf_page",
            "gradient": "from-green-500 to-green-600",
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
        },
    }

    # Detect current tool from URL
    path = request.path.strip("/")
    language_code = get_language()
    if path.startswith(f"{language_code}/"):
        path = path[len(language_code) + 1 :]

    # Map URL patterns to tool keys
    url_to_tool = {
        "pdf-to-word": "pdf_to_word",
        "word-to-pdf": "word_to_pdf",
        "pdf-to-jpg": "pdf_to_jpg",
        "jpg-to-pdf": "jpg_to_pdf",
        "pdf-to-excel": "pdf_to_excel",
        "excel-to-pdf": "excel_to_pdf",
        "pdf-to-ppt": "pdf_to_ppt",
        "ppt-to-pdf": "ppt_to_pdf",
        "pdf-to-html": "pdf_to_html",
        "html-to-pdf": "html_to_pdf",
        "pdf-organize/merge": "merge_pdf",
        "pdf-organize/split": "split_pdf",
        "pdf-organize/compress": "compress_pdf",
        "pdf-organize/extract-pages": "extract_pages",
        "pdf-organize/remove-pages": "remove_pages",
        "pdf-organize/organize": "organize_pdf",
        "pdf-edit/rotate": "rotate_pdf",
        "pdf-edit/crop": "crop_pdf",
        "pdf-edit/add-watermark": "add_watermark",
        "pdf-edit/add-page-numbers": "add_page_numbers",
        "pdf-security/protect": "protect_pdf",
        "pdf-security/unlock": "unlock_pdf",
    }

    current_tool = None
    for url_pattern, tool_key in url_to_tool.items():
        if url_pattern in path:
            current_tool = tool_key
            break

    # Get related tools
    related_tools_list = []
    if current_tool and current_tool in tools_map:
        related_keys = tools_map[current_tool][:6]
        for tool_key in related_keys:
            if tool_key in tools_info:
                tool_data = tools_info[tool_key].copy()
                try:
                    tool_data["url"] = reverse(tool_data["url_name"])
                except Exception:
                    continue
                related_tools_list.append(tool_data)

    return {"related_tools": related_tools_list}
