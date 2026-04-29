# utils_site/src/frontend/views.py

from datetime import datetime
from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import TemplateView
from src.frontend.tool_configs import BATCH_API_MAP, TOOL_CONFIGS


def anonymous_cache_page(timeout):
    """Cache page only for anonymous users.

    Authenticated users always get fresh responses (needed for premium-specific content).
    Anonymous users get cached responses for better performance.
    Cache varies by cookie to keep CSRF tokens valid in cached templates.
    """

    def decorator(view_func):
        # `cache_page` must wrap a view that already sets `Vary: Cookie`,
        # otherwise cache keys won't include cookie-specific variants.
        # `ensure_csrf_cookie` must be outside cache to guarantee csrftoken
        # on cache hits for anonymous visitors (language switch form uses POST).
        cached_view = ensure_csrf_cookie(cache_page(timeout)(vary_on_cookie(view_func)))
        uncached_view = ensure_csrf_cookie(view_func)

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                return uncached_view(request, *args, **kwargs)
            return cached_view(request, *args, **kwargs)

        return wrapper

    return decorator


def _is_premium_active_user(request) -> bool:
    """Check whether request user has active premium subscription."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    return bool(
        getattr(user, "is_premium_active", False)
        or (
            getattr(user, "is_premium", False)
            and hasattr(user, "is_subscription_active")
            and user.is_subscription_active()
        )
    )


def _redirect_for_premium_access(request):
    """Redirect non-premium users to login or pricing for premium-only pages."""
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        return redirect("frontend:pricing")
    login_url = reverse("users:login")
    return redirect(f"{login_url}?next={request.path}")


def _get_related_tools(current_tool):
    """Get related tools for internal linking."""
    all_tools = {
        "pdf_to_word": {
            "name": _("PDF to Word"),
            "url": "frontend:pdf_to_word_page",
            "description": _("Convert PDF to editable Word documents"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
        },
        "word_to_pdf": {
            "name": _("Word to PDF"),
            "url": "frontend:word_to_pdf_page",
            "description": _("Convert Word documents to PDF format"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>',
            "gradient": "from-red-500 to-red-600",
        },
        "pdf_to_jpg": {
            "name": _("PDF to JPG"),
            "url": "frontend:pdf_to_jpg_page",
            "description": _("Convert PDF pages to JPG images"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-green-500 to-green-600",
        },
        "jpg_to_pdf": {
            "name": _("JPG to PDF"),
            "url": "frontend:jpg_to_pdf_page",
            "description": _("Convert images to PDF documents"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
        },
        "merge_pdf": {
            "name": _("Merge PDF"),
            "url": "frontend:merge_pdf_page",
            "description": _("Combine multiple PDFs into one"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>',
            "gradient": "from-indigo-500 to-indigo-600",
        },
        "split_pdf": {
            "name": _("Split PDF"),
            "url": "frontend:split_pdf_page",
            "description": _("Split PDF into multiple files"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-orange-500 to-orange-600",
        },
        "compress_pdf": {
            "name": _("Compress PDF"),
            "url": "frontend:compress_pdf_page",
            "description": _("Reduce PDF file size"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>',
            "gradient": "from-teal-500 to-teal-600",
        },
        "rotate_pdf": {
            "name": _("Rotate PDF"),
            "url": "frontend:rotate_pdf_page",
            "description": _("Rotate PDF pages"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
            "gradient": "from-cyan-500 to-cyan-600",
        },
        "protect_pdf": {
            "name": _("Protect PDF"),
            "url": "frontend:protect_pdf_page",
            "description": _("Add password protection"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-red-500 to-pink-600",
        },
        "unlock_pdf": {
            "name": _("Unlock PDF"),
            "url": "frontend:unlock_pdf_page",
            "description": _("Remove PDF password"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
            "gradient": "from-green-500 to-emerald-600",
        },
        "pdf_to_excel": {
            "name": _("PDF to Excel"),
            "url": "frontend:pdf_to_excel_page",
            "description": _("Extract tables to Excel"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
            "gradient": "from-green-600 to-green-700",
        },
        "organize_pdf": {
            "name": _("Organize PDF"),
            "url": "frontend:organize_pdf_page",
            "description": _("Reorder PDF pages"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
            "gradient": "from-violet-500 to-violet-600",
        },
        "epub_to_pdf": {
            "name": _("EPUB to PDF"),
            "url": "frontend:epub_to_pdf_page",
            "description": _("Convert EPUB eBooks to PDF"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h10M7 12h10M7 17h6"/>',
            "gradient": "from-amber-500 to-orange-600",
        },
        "pdf_to_epub": {
            "name": _("PDF to EPUB"),
            "url": "frontend:pdf_to_epub_page",
            "description": _("Convert PDFs to EPUB eBooks"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7h12M4 12h8m-8 5h12m4-10v10a2 2 0 01-2 2h-1"/>',
            "gradient": "from-amber-500 to-orange-600",
        },
        "pdf_to_markdown": {
            "name": _("PDF to Markdown"),
            "url": "frontend:pdf_to_markdown_page",
            "description": _("Convert PDF to structured Markdown"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h10M4 18h7m8-6l2 2 4-4"/>',
            "gradient": "from-amber-500 to-orange-600",
        },
        "compare_pdf": {
            "name": _("Compare Two PDFs"),
            "url": "frontend:compare_pdf_page",
            "description": _("Visual diff and change report for two PDFs"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9H6a2 2 0 00-2 2v7a2 2 0 002 2h4m4-11h4a2 2 0 012 2v7a2 2 0 01-2 2h-4m-4-11v11m0 0l-2-2m2 2l2-2"/>',
            "gradient": "from-amber-500 to-orange-600",
        },
        # Tools without a previous entry — they exist as views but didn't
        # appear as a related-tool target anywhere, so other pages couldn't
        # link back to them. Adding them here lets the relations map below
        # surface them as incoming links from sibling tools.
        "flatten_pdf": {
            "name": _("Flatten PDF"),
            "url": "frontend:flatten_pdf_page",
            "description": _("Remove form fields and annotations"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
            "gradient": "from-cyan-500 to-blue-600",
        },
        "sign_pdf": {
            "name": _("Sign PDF"),
            "url": "frontend:sign_pdf_page",
            "description": _("Add an image signature to PDF pages"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>',
            "gradient": "from-amber-500 to-orange-600",
        },
        "pdf_to_text": {
            "name": _("PDF to Text"),
            "url": "frontend:pdf_to_text_page",
            "description": _("Extract plain text from a PDF document"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>',
            "gradient": "from-slate-500 to-slate-600",
        },
        "optimize_image": {
            "name": _("Optimize Image"),
            "url": "frontend:optimize_image_page",
            "description": _("Compress and resize JPEG/PNG/WebP images"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-emerald-500 to-emerald-600",
        },
        "convert_image": {
            "name": _("Convert Image"),
            "url": "frontend:convert_image_page",
            "description": _("Convert between JPEG, PNG, WebP, GIF and BMP"),
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-pink-500 to-pink-600",
        },
    }

    # Define related tools for each tool. Each tool gets 3 outgoing links;
    # collectively the map ensures every tool appears as a related target on
    # at least 2 sibling pages (closes Ahrefs' "only one dofollow incoming
    # internal link" warnings on the long-tail tool pages).
    relations = {
        "pdf_to_word": ["word_to_pdf", "pdf_to_excel", "pdf_to_text"],
        "word_to_pdf": ["pdf_to_word", "merge_pdf", "compress_pdf"],
        "pdf_to_jpg": ["jpg_to_pdf", "convert_image", "split_pdf"],
        "jpg_to_pdf": ["pdf_to_jpg", "optimize_image", "convert_image"],
        "rotate_pdf": ["organize_pdf", "crop_pdf", "flatten_pdf"],
        "add_page_numbers": ["rotate_pdf", "organize_pdf", "add_watermark"],
        "add_watermark": ["protect_pdf", "sign_pdf", "flatten_pdf"],
        "crop_pdf": ["rotate_pdf", "compress_pdf", "organize_pdf"],
        "merge_pdf": ["split_pdf", "compress_pdf", "organize_pdf"],
        "split_pdf": ["merge_pdf", "extract_pages", "organize_pdf"],
        "remove_pages": ["split_pdf", "organize_pdf", "extract_pages"],
        "extract_pages": ["split_pdf", "merge_pdf", "remove_pages"],
        "organize_pdf": ["merge_pdf", "split_pdf", "rotate_pdf"],
        "pdf_to_excel": ["pdf_to_word", "merge_pdf", "pdf_to_text"],
        "excel_to_pdf": ["pdf_to_excel", "merge_pdf", "compress_pdf"],
        "ppt_to_pdf": ["merge_pdf", "compress_pdf", "protect_pdf"],
        "html_to_pdf": ["merge_pdf", "compress_pdf", "pdf_to_text"],
        "pdf_to_ppt": ["merge_pdf", "compress_pdf", "split_pdf"],
        "pdf_to_html": ["pdf_to_word", "pdf_to_text", "split_pdf"],
        "epub_to_pdf": ["pdf_to_epub", "pdf_to_word", "pdf_to_jpg"],
        "pdf_to_epub": ["epub_to_pdf", "pdf_to_word", "pdf_to_text"],
        "pdf_to_markdown": ["pdf_to_word", "pdf_to_html", "pdf_to_text"],
        "compare_pdf": ["pdf_to_markdown", "compress_pdf", "split_pdf"],
        "compress_pdf": ["merge_pdf", "optimize_image", "protect_pdf"],
        "protect_pdf": ["unlock_pdf", "sign_pdf", "flatten_pdf"],
        "unlock_pdf": ["protect_pdf", "compress_pdf", "merge_pdf"],
        # Below: tool keys that previously had no relations entry, so the
        # related_tools block on their pages was empty. Each tool now points
        # at three siblings to give every page at least three outgoing
        # internal links — closes the "only one dofollow incoming internal
        # link" warnings on these tool/category pairs.
        "flatten_pdf": ["add_watermark", "rotate_pdf", "organize_pdf"],
        "sign_pdf": ["add_watermark", "protect_pdf", "flatten_pdf"],
        "pdf_to_text": ["pdf_to_word", "pdf_to_markdown", "split_pdf"],
        "optimize_image": ["convert_image", "jpg_to_pdf", "compress_pdf"],
        "convert_image": ["optimize_image", "jpg_to_pdf", "pdf_to_jpg"],
    }

    related_keys = relations.get(current_tool, [])
    result = []
    for key in related_keys:
        if key in all_tools:
            tool = all_tools[key].copy()
            tool["url"] = reverse(tool["url"])
            result.append(tool)
    return result


@anonymous_cache_page(60 * 60)
def index_page(request):
    """Home page view."""
    from django.core.cache import cache
    from src.blog.models import Article

    # Cache latest articles for 1 hour
    cache_key = "homepage_latest_articles"
    latest_articles = cache.get(cache_key)

    if latest_articles is None:
        latest_articles = list(
            Article.objects.filter(status="published")
            .select_related("category")
            .order_by("-published_at", "-created_at")[:2]
        )
        cache.set(cache_key, latest_articles, 3600)  # Cache for 1 hour

    # Используем отдельные вызовы gettext_lazy для каждой строки
    page_title = _("Convertica – Online PDF ↔ Word Converter")
    page_description = _(
        "Fast, simple and secure online PDF to Word and Word to PDF converter. "
        "Convert documents instantly, no registration required."
    )

    # Ключевые слова остаются на английском для SEO
    page_keywords = (
        "PDF to Word, Word to PDF, PDF converter, DOCX converter, online converter, "
        "free converter, convert PDF, convert Word, free pdf tools online, "
        "pdf tools no registration, best pdf converter online, pdf editor online free, "
        "pdf tools for students, pdf tools for business, smallpdf alternative, "
        "ilovepdf alternative, adobe acrobat alternative, free pdf converter, "
        "pdf merger online, pdf splitter online, pdf compressor online, "
        "pdf rotator online, pdf watermark tool, high quality pdf converter, "
        "pdf converter no quality loss, pdf converter best quality, "
        "pdf converter for mac, pdf converter for windows, pdf converter for linux, "
        "pdf converter mobile"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
        "latest_articles": latest_articles,
    }
    return render(request, "frontend/index.html", context)


def _get_converter_context(
    request,
    page_title: str,
    page_description: str,
    page_keywords: str,
    page_subtitle: str,
    header_text: str,
    file_input_name: str,
    file_accept: str,
    api_url_name: str,
    replace_regex: str,
    replace_to: str,
    button_text: str,
    select_file_message: str,
    button_class: str = "bg-blue-600 text-white hover:bg-blue-700",
) -> dict:
    """Helper function to generate converter page context.

    IMPORTANT: All translatable parameters must be passed already wrapped in _()
    from the calling function.

    Args:
        request: HTTP request object
        page_title: Already translated page title (wrapped in _() by caller)
        page_description: Already translated page description
        page_keywords: English keywords (not translated for SEO)
        page_subtitle: Already translated page subtitle
        header_text: Already translated header text
        file_input_name: Name of the file input field
        file_accept: Accepted file extensions (e.g., '.pdf' or '.doc,.docx')
        api_url_name: Name of the API URL pattern
        replace_regex: Regex pattern for filename replacement
        replace_to: Replacement string for filename
        button_text: Already translated button text
        select_file_message: Already translated select file message
        button_class: CSS classes for the convert button

    Returns:
        dict: Context dictionary for the template
    """
    # Check if user has active premium subscription
    is_premium_active = False
    if hasattr(request, "user") and request.user.is_authenticated:
        is_premium_active = bool(
            getattr(request.user, "is_premium_active", False)
            or (
                request.user.is_premium
                and hasattr(request.user, "is_subscription_active")
                and request.user.is_subscription_active()
            )
        )

    batch_enabled = False
    batch_api_url = ""
    batch_field_name = ""
    if is_premium_active:
        batch_entry = BATCH_API_MAP.get(api_url_name)
        if batch_entry:
            batch_enabled = True
            batch_api_url = reverse(batch_entry["batch_url"])
            batch_field_name = batch_entry["field_name"]

    # Surface effective file-size limits to the template so the upload widget
    # can show the user "up to NN MB" instead of letting them upload, wait,
    # then fail. Values are in megabytes for direct display.
    free_mb = int(settings.MAX_FILE_SIZE_FREE / (1024 * 1024))
    premium_mb = int(settings.MAX_FILE_SIZE_PREMIUM / (1024 * 1024))

    return {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
        "page_subtitle": page_subtitle,
        "header_text": header_text,
        "file_input_name": file_input_name,
        "file_accept": file_accept,
        "button_class": button_class,
        "button_text": button_text,
        "select_file_message": select_file_message,
        "api_url": reverse(api_url_name),
        "replace_regex": replace_regex,
        "replace_to": replace_to,
        "error_message": _("Conversion failed. Please try again."),
        "is_premium": is_premium_active,
        "batch_enabled": batch_enabled,
        "batch_api_url": batch_api_url,
        "batch_field_name": batch_field_name,
        "max_file_size_mb_free": free_mb,
        "max_file_size_mb_premium": premium_mb,
        "max_file_size_mb_current": premium_mb if is_premium_active else free_mb,
        # Signal base.html to auto-generate SoftwareApplication + HowTo schema.
        # Set to False in specific views that define their own structured_data block.
        "auto_generate_tool_schema": True,
    }


def _render_tool_page(request, tool_key: str) -> HttpResponse:
    """Generic renderer for the 25 standard tool pages.

    Reads configuration from TOOL_CONFIGS[tool_key], builds context via
    _get_converter_context(), merges SEO data and optional extras, then renders.
    """
    config = TOOL_CONFIGS[tool_key]
    context = _get_converter_context(request, **config["converter_args"])
    context.update(config["seo"])
    context["related_tools"] = _get_related_tools(tool_key)
    if "extra" in config:
        context.update(config["extra"])
    return render(request, config["template"], context)


@anonymous_cache_page(60 * 60)
def pdf_to_word_page(request):
    """PDF to Word conversion page."""
    return _render_tool_page(request, "pdf_to_word")


@anonymous_cache_page(60 * 60)
def word_to_pdf_page(request):
    """Word to PDF conversion page."""
    return _render_tool_page(request, "word_to_pdf")


@anonymous_cache_page(60 * 60)
def pdf_to_jpg_page(request):
    """PDF to JPG conversion page."""
    return _render_tool_page(request, "pdf_to_jpg")


@anonymous_cache_page(60 * 60)
def jpg_to_pdf_page(request):
    """JPG to PDF conversion page."""
    return _render_tool_page(request, "jpg_to_pdf")


@anonymous_cache_page(60 * 60)
def rotate_pdf_page(request):
    """Rotate PDF page."""
    return _render_tool_page(request, "rotate_pdf")


@anonymous_cache_page(60 * 60)
def add_page_numbers_page(request):
    """Add page numbers to PDF page."""
    return _render_tool_page(request, "add_page_numbers")


@anonymous_cache_page(60 * 60)
def add_watermark_page(request):
    """Add watermark to PDF page."""
    return _render_tool_page(request, "add_watermark")


@anonymous_cache_page(60 * 60)
def crop_pdf_page(request):
    """Crop PDF page."""
    return _render_tool_page(request, "crop_pdf")


@anonymous_cache_page(60 * 60)
def flatten_pdf_page(request):
    """Flatten PDF page."""
    return _render_tool_page(request, "flatten_pdf")


@anonymous_cache_page(60 * 60)
def sign_pdf_page(request):
    """Sign PDF page."""
    return _render_tool_page(request, "sign_pdf")


@anonymous_cache_page(60 * 60)
def optimize_image_page(request):
    """Optimize image page."""
    return _render_tool_page(request, "optimize_image")


@anonymous_cache_page(60 * 60)
def convert_image_page(request):
    """Convert image page."""
    return _render_tool_page(request, "convert_image")


@anonymous_cache_page(60 * 60)
def merge_pdf_page(request):
    """Merge PDF page."""
    return _render_tool_page(request, "merge_pdf")


@anonymous_cache_page(60 * 60)
def split_pdf_page(request):
    """Split PDF page."""
    return _render_tool_page(request, "split_pdf")


@anonymous_cache_page(60 * 60)
def remove_pages_page(request):
    """Remove pages from PDF page."""
    return _render_tool_page(request, "remove_pages")


@anonymous_cache_page(60 * 60)
def extract_pages_page(request):
    """Extract pages from PDF page."""
    return _render_tool_page(request, "extract_pages")


@anonymous_cache_page(60 * 60)
def organize_pdf_page(request):
    """Organize PDF page."""
    return _render_tool_page(request, "organize_pdf")


@anonymous_cache_page(60 * 60)
def pdf_to_excel_page(request):
    """PDF to Excel conversion page."""
    return _render_tool_page(request, "pdf_to_excel")


@anonymous_cache_page(60 * 60)
def excel_to_pdf_page(request):
    """Excel to PDF conversion page."""
    return _render_tool_page(request, "excel_to_pdf")


@anonymous_cache_page(60 * 60)
def ppt_to_pdf_page(request):
    """PowerPoint to PDF conversion page."""
    return _render_tool_page(request, "ppt_to_pdf")


@anonymous_cache_page(60 * 60)
def html_to_pdf_page(request):
    """HTML to PDF conversion page."""
    return _render_tool_page(request, "html_to_pdf")


@anonymous_cache_page(60 * 60)
def pdf_to_ppt_page(request):
    """PDF to PowerPoint conversion page."""
    return _render_tool_page(request, "pdf_to_ppt")


@anonymous_cache_page(60 * 60)
def pdf_to_html_page(request):
    """PDF to HTML conversion page."""
    return _render_tool_page(request, "pdf_to_html")


@anonymous_cache_page(60 * 60)
def compress_pdf_page(request):
    """Compress PDF page."""
    return _render_tool_page(request, "compress_pdf")


@anonymous_cache_page(60 * 60)
def protect_pdf_page(request):
    """Protect PDF page."""
    return _render_tool_page(request, "protect_pdf")


@anonymous_cache_page(60 * 60)
def unlock_pdf_page(request):
    """Unlock PDF page."""
    return _render_tool_page(request, "unlock_pdf")


def all_tools_page(request):
    """All Tools page - shows all PDF tools organized by categories."""

    page_title = _("All PDF Tools - Convertica")
    page_description = _(
        "Browse all PDF tools: Convert, Edit, Organize, and Secure PDFs. "
        "Free online PDF tools for all your document needs."
    )

    page_keywords = (
        "PDF tools, PDF converter, PDF editor, PDF organizer, "
        "PDF security, all PDF tools, online PDF tools, free PDF tools, "
        "free pdf tools online, pdf tools no registration, "
        "best pdf converter online, pdf editor online free, "
        "pdf tools for students, pdf tools for business, "
        "smallpdf alternative, ilovepdf alternative, adobe acrobat alternative, "
        "free pdf converter, pdf merger online, pdf splitter online, "
        "pdf compressor online, pdf rotator online, pdf watermark tool, "
        "high quality pdf converter, pdf converter no quality loss, "
        "pdf converter best quality, pdf converter for mac, "
        "pdf converter for windows, pdf converter for linux, pdf converter mobile, "
        "convert pdf to word for resume, merge pdf for thesis, "
        "compress pdf for email attachment, split pdf by chapters"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
    }
    return render(request, "frontend/all_tools.html", context)


@anonymous_cache_page(60 * 60)
def premium_tools_page(request):
    """Premium tools catalog page."""
    page_title = _("Premium Tools - Convertica")
    page_description = _(
        "Explore Convertica Premium tools and features: advanced conversion workflows, "
        "higher limits, priority processing, and early access to new formats."
    )
    page_keywords = (
        "premium pdf tools, advanced pdf converter, epub to pdf premium, "
        "pdf to epub premium, pdf to markdown premium, compare pdf premium, "
        "batch conversion premium, ocr premium, "
        "priority queue pdf conversion, background tasks pdf converter"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
        "is_premium_active": _is_premium_active_user(request),
        "premium_tool_entities": [
            {
                "name": _("EPUB to PDF"),
                "url": reverse("frontend:epub_to_pdf_page"),
                "description": _(
                    "Convert EPUB eBooks to PDF with premium rendering quality."
                ),
            },
            {
                "name": _("PDF to EPUB"),
                "url": reverse("frontend:pdf_to_epub_page"),
                "description": _(
                    "Convert PDF files into EPUB for eReaders and mobile reading apps."
                ),
            },
            {
                "name": _("PDF to Markdown"),
                "url": reverse("frontend:pdf_to_markdown_page"),
                "description": _(
                    "Extract structured Markdown from PDF documents, including headings and tables."
                ),
            },
            {
                "name": _("Compare Two PDFs"),
                "url": reverse("frontend:compare_pdf_page"),
                "description": _(
                    "Generate visual diff outputs and detailed comparison reports for PDF revisions."
                ),
            },
            {
                "name": _("Scanned PDF to Word"),
                "url": reverse("frontend:ocr_pdf_to_word_page"),
                "description": _(
                    "Convert scanned or image-based PDFs to editable DOCX with OCR."
                ),
            },
            {
                "name": _("Batch Converter Hub"),
                "url": reverse("frontend:batch_converter_page"),
                "description": _(
                    "Run bulk conversions across supported premium workflows."
                ),
            },
            {
                "name": _("Saved Workflows"),
                "url": reverse("frontend:premium_workflows_page"),
                "description": _(
                    "Store reusable conversion presets and relaunch them in one click."
                ),
            },
            {
                "name": _("Background Queue Center"),
                "url": reverse("frontend:background_center_page"),
                "description": _(
                    "Track long-running premium tasks and download finished files."
                ),
            },
            {
                "name": _("Sign PDF"),
                "url": reverse("frontend:sign_pdf_page"),
                "description": _(
                    "Add your handwritten signature image to any PDF page. Choose position, size, and opacity. Apply to all pages at once."
                ),
            },
            {
                "name": _("PDF to Text"),
                "url": reverse("frontend:pdf_to_text_page"),
                "description": _(
                    "Extract all text content from a PDF as a plain .txt file. Supports page numbering and layout preservation."
                ),
            },
        ],
    }
    return render(request, "frontend/premium_tools.html", context)


@anonymous_cache_page(60 * 60)
def epub_to_pdf_page(request):
    """EPUB to PDF conversion landing page (premium-gated API)."""
    return _render_tool_page(request, "epub_to_pdf")


@anonymous_cache_page(60 * 60)
def pdf_to_epub_page(request):
    """PDF to EPUB conversion landing page (premium-gated API)."""
    return _render_tool_page(request, "pdf_to_epub")


@anonymous_cache_page(60 * 60)
def pdf_to_markdown_page(request):
    """PDF to Markdown conversion landing page (premium-gated API)."""
    return _render_tool_page(request, "pdf_to_markdown")


@anonymous_cache_page(60 * 60)
def pdf_to_text_page(request):
    """PDF to Text conversion page."""
    return _render_tool_page(request, "pdf_to_text")


@anonymous_cache_page(60 * 60)
def compare_pdf_page(request):
    """Compare two PDF files with visual diff and report (premium-gated API)."""

    context = {
        "page_title": _("Compare Two PDFs (Premium) - Convertica"),
        "page_description": _(
            "Compare two PDF files with visual diff overlays and detailed change reports. "
            "Download a ZIP package with per-page comparison assets."
        ),
        "page_keywords": (
            "compare pdf files premium, pdf diff checker, visual pdf compare, "
            "pdf change report, compare two pdf documents online"
        ),
        "page_subtitle": _(
            "Upload two PDFs to generate a visual diff and downloadable report"
        ),
        "header_text": _("Compare Two PDFs"),
        "api_url": reverse("compare_pdf_api"),
        "is_premium": _is_premium_active_user(request),
        "related_tools": _get_related_tools("compare_pdf"),
        "page_content_title": _(
            "Compare PDF revisions with visual diffs and change reports"
        ),
        "page_content_body": _(
            "<p><strong>Compare Two PDFs</strong> helps review document revisions using "
            "page-level visual overlays and exportable reports. It is useful for contracts, "
            "technical documentation, and regulated approval workflows.</p>"
            "<p>The generated ZIP includes diff images and structured summaries so teams can "
            "track what changed without manually checking each page.</p>"
            "<p>Use the sensitivity slider to control how strict visual detection should be "
            "for minor typography shifts versus major layout edits.</p>"
        ),
        "benefits_title": _("Why use Compare Two PDFs in Premium?"),
        "page_benefits": [
            {
                "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9H6a2 2 0 00-2 2v7a2 2 0 002 2h4m4-11h4a2 2 0 012 2v7a2 2 0 01-2 2h-4m-4-11v11m0 0l-2-2m2 2l2-2"/>',
                "gradient": "from-amber-500 to-orange-600",
                "title": _("Visual page diff"),
                "description": _(
                    "Highlights changed zones on each page for faster manual review."
                ),
            },
            {
                "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h10"/>',
                "gradient": "from-blue-500 to-indigo-600",
                "title": _("Machine-readable reports"),
                "description": _(
                    "Exports Markdown and JSON summaries for audit or automation workflows."
                ),
            },
            {
                "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
                "gradient": "from-emerald-500 to-teal-600",
                "title": _("Configurable sensitivity"),
                "description": _(
                    "Tune change detection to catch subtle edits or focus on large differences."
                ),
            },
        ],
        "tips_title": _("Tips for Better PDF Comparison Accuracy"),
        "page_tips": [
            _("Compare files with matching page size and orientation when possible."),
            _(
                "Use lower sensitivity for subtle text edits and higher values for layout changes."
            ),
            _(
                "Ensure both documents are fully rendered exports, not partial draft snapshots."
            ),
            _(
                "Review generated diff images together with report metrics for best decisions."
            ),
        ],
        "faq_title": _("Compare PDF FAQ"),
        "page_faq": [
            {
                "question": _("What does Compare Two PDFs generate?"),
                "answer": _(
                    "The tool creates a ZIP package with visual page-by-page diff images and structured change reports (Markdown and JSON)."
                ),
            },
            {
                "question": _("Can I tune comparison sensitivity?"),
                "answer": _(
                    "Yes. Use the sensitivity slider to control how strictly visual differences are highlighted."
                ),
            },
            {
                "question": _("Is PDF compare available for free users?"),
                "answer": _(
                    "The comparison workflow is a premium feature. Landing pages are public, but API usage requires premium access."
                ),
            },
        ],
    }
    context["auto_generate_tool_schema"] = False  # template has its own schema
    return render(request, "frontend/premium/compare_pdf.html", context)


@anonymous_cache_page(60 * 60)
def ocr_pdf_to_word_page(request):
    """Premium OCR flow for scanned PDF to Word."""
    if not _is_premium_active_user(request):
        return _redirect_for_premium_access(request)

    context = {
        "page_title": _("Scanned PDF to Word (OCR) - Convertica"),
        "page_description": _(
            "Convert scanned PDFs and image-based documents to editable Word "
            "files with premium OCR tools."
        ),
        "page_keywords": (
            "scanned pdf to word, ocr pdf to word, premium ocr converter, "
            "image pdf to editable docx, extract text from scanned pdf"
        ),
        "ocr_converter_url": f"{reverse('frontend:pdf_to_word_page')}?ocr=1",
    }
    return render(request, "frontend/premium/ocr_pdf_to_word.html", context)


@anonymous_cache_page(60 * 60)
def batch_converter_page(request):
    """Premium batch conversion hub page."""
    if not _is_premium_active_user(request):
        return _redirect_for_premium_access(request)

    context = {
        "page_title": _("Batch Converter Hub (Premium) - Convertica"),
        "page_description": _(
            "Convert multiple files in one run with premium batch conversion "
            "workflows and background processing support."
        ),
        "page_keywords": (
            "batch pdf converter premium, convert multiple files to pdf, "
            "bulk document conversion, premium batch tools"
        ),
        "batch_tools": [
            {
                "name": _("PDF to Word"),
                "description": _("Convert multiple PDFs to editable DOCX in one run."),
                "url": reverse("frontend:pdf_to_word_page"),
            },
            {
                "name": _("Word to PDF"),
                "description": _("Export multiple DOC or DOCX files to PDF."),
                "url": reverse("frontend:word_to_pdf_page"),
            },
            {
                "name": _("PDF to JPG"),
                "description": _("Generate image sets from multiple PDF files."),
                "url": reverse("frontend:pdf_to_jpg_page"),
            },
            {
                "name": _("JPG to PDF"),
                "description": _("Bundle multiple images into one or more PDFs."),
                "url": reverse("frontend:jpg_to_pdf_page"),
            },
            {
                "name": _("Compress PDF"),
                "description": _("Reduce size for multiple PDFs in one operation."),
                "url": reverse("frontend:compress_pdf_page"),
            },
            {
                "name": _("Add Watermark"),
                "description": _("Apply one watermark preset across multiple PDFs."),
                "url": reverse("frontend:add_watermark_page"),
            },
        ],
    }
    return render(request, "frontend/premium/batch_converter.html", context)


@anonymous_cache_page(60 * 60)
def premium_workflows_page(request):
    """Premium saved workflows page."""
    if not _is_premium_active_user(request):
        return _redirect_for_premium_access(request)

    context = {
        "page_title": _("Saved Workflows (Premium) - Convertica"),
        "page_description": _(
            "Create and reuse premium conversion presets with preconfigured "
            "parameters for frequent tasks."
        ),
        "page_keywords": (
            "premium workflows, conversion presets, saved converter settings, "
            "ocr workflow presets, pdf automation"
        ),
    }
    return render(request, "frontend/premium/workflows.html", context)


@anonymous_cache_page(60 * 60)
def background_center_page(request):
    """Premium background queue center page."""
    if not _is_premium_active_user(request):
        return _redirect_for_premium_access(request)

    context = {
        "page_title": _("Background Queue Center (Premium) - Convertica"),
        "page_description": _(
            "Monitor premium background conversions, download completed files, "
            "and manage queued tasks from one dashboard."
        ),
        "page_keywords": (
            "background queue premium, conversion queue dashboard, "
            "background pdf tasks, async conversion monitor"
        ),
    }
    return render(request, "frontend/premium/background_center.html", context)


@ensure_csrf_cookie
@vary_on_cookie
@cache_page(60 * 60 * 24 * 7)
def about_page(request):
    """About Us page."""
    page_title = _("About Us - Convertica")
    page_description = _(
        "Learn about Convertica - your trusted online PDF tools platform. "
        "We are committed to constant improvement and providing the best "
        "PDF conversion and editing experience."
    )
    page_keywords = _(
        "about Convertica, PDF tools company, "
        "online PDF converter, PDF services, document conversion"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
    }
    return render(request, "frontend/about.html", context)


@ensure_csrf_cookie
@vary_on_cookie
@cache_page(60 * 60 * 24 * 7)
def privacy_page(request):
    """Privacy Policy page."""
    page_title = _("Privacy Policy - Convertica")
    page_description = _(
        "Read Convertica's Privacy Policy. "
        "Learn how we protect your data and handle your files. "
        "Your privacy is our priority."
    )
    page_keywords = _(
        "privacy policy, data protection, file security, " "privacy, Convertica privacy"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
    }
    return render(request, "frontend/privacy.html", context)


@ensure_csrf_cookie
@vary_on_cookie
@cache_page(60 * 60 * 24 * 7)
def terms_page(request):
    """Terms of Service page."""
    page_title = _("Terms of Service - Convertica")
    page_description = _(
        "Read Convertica's Terms of Service. Understand the terms, conditions, "
        "and acceptable use policy for our free online PDF tools — conversion, "
        "editing, merging, splitting, compression, and security features."
    )
    page_keywords = _(
        "terms of service, terms and conditions, " "user agreement, Convertica terms"
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
    }
    return render(request, "frontend/terms.html", context)


@ensure_csrf_cookie
def contact_page(request):
    """Contact page with form handling."""
    from django.contrib import messages
    from django.shortcuts import redirect

    from .forms import ContactForm

    if request.method == "GET" and "sent" in request.GET:
        messages.success(
            request,
            _(
                "Thank you! Your message has been sent successfully. "
                "We'll get back to you as soon as possible, usually within 24-48 hours."
            ),
        )

    form = ContactForm()
    message_sent = False

    if request.method == "POST":
        form = ContactForm(request.POST)

        from src.api.spam_protection import verify_turnstile

        turnstile_token = request.POST.get("turnstile_token", "") or request.POST.get(
            "cf-turnstile-response", ""
        )

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            remote_ip = x_forwarded_for.split(",")[0].strip()
        else:
            remote_ip = request.META.get("REMOTE_ADDR", "")

        if not verify_turnstile(turnstile_token, remote_ip):
            messages.error(
                request,
                _("Please complete the CAPTCHA verification."),
            )

            page_title = _("Contact Us - Convertica")
            page_description = _(
                "Contact Convertica for support, questions, or feedback. "
                "We're here to help with all your PDF tool needs."
            )
            page_keywords = _(
                "contact Convertica, support, customer service, help, feedback"
            )

            return render(
                request,
                "frontend/contact.html",
                {
                    "page_title": page_title,
                    "page_description": page_description,
                    "page_keywords": page_keywords,
                    "form": form,
                    "message_sent": False,
                },
            )

        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            user_ip = request.META.get("REMOTE_ADDR", "Unknown")

            telegram_enabled = getattr(settings, "CONTACT_TELEGRAM_ENABLED", False)

            if telegram_enabled:
                from src.tasks.telegram_service import send_telegram_message

                telegram_message = f"""
<b>📩 New contact form submission</b>

<b>Name:</b> {name}
<b>Email:</b> {email}
<b>Subject:</b> {subject}

<b>Message:</b>
{message}

<b>IP:</b> {user_ip}
"""

                send_telegram_message.delay(
                    text=telegram_message,
                )

            else:
                from src.tasks.email import send_contact_form_email

                recipient_email = getattr(
                    settings, "CONTACT_EMAIL", "info@convertica.net"
                )
                from_email = getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    f"noreply@{request.get_host()}",
                )

                email_subject = f"[Convertica Contact] {subject}"
                email_body = f"""New contact form submission from Convertica website:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

---
This message was sent from the contact form on {request.build_absolute_uri('/contact/')}
IP Address: {user_ip}
User Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}
"""

                send_contact_form_email.delay(
                    subject=email_subject,
                    message=email_body,
                    from_email=from_email,
                    recipient_email=recipient_email,
                    user_email=email,
                    user_ip=user_ip,
                )

            return redirect(f"{request.path}?sent=1")

        else:
            messages.error(
                request,
                _("Please correct the errors in the form below."),
            )

    page_title = _("Contact Us - Convertica")
    page_description = _(
        "Contact Convertica for support, questions, or feedback. "
        "We're here to help with all your PDF tool needs."
    )
    page_keywords = _("contact Convertica, support, customer service, help, feedback")

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
        "form": form,
        "message_sent": message_sent,
        # Contact form always renders a Turnstile widget — opt in to loading
        # the script (base.html otherwise skips it on non-form pages).
        "needs_turnstile": True,
    }

    return render(request, "frontend/contact.html", context)


@ensure_csrf_cookie
@vary_on_cookie
@cache_page(60 * 60 * 24)
def faq_page(request):
    """FAQ page with proper CSRF handling."""
    page_title = _("Frequently Asked Questions (FAQ) - Convertica")
    page_description = _(
        "Find answers to frequently asked questions about Convertica PDF tools. "
        "Learn how to convert, edit, and organize PDF files online for free."
    )

    page_keywords = (
        "FAQ, frequently asked questions, PDF converter help, PDF tools FAQ, "
        "how to convert PDF, PDF questions, convert pdf to word online free, "
        "pdf to word without losing formatting, compress pdf online free, "
        "merge pdf online free, split pdf online free, pdf to jpg online free, "
        "jpg to pdf online free, pdf to excel online free, word to pdf online free, "
        "rotate pdf online free, add watermark to pdf online free, "
        "crop pdf online free, protect pdf online free, unlock pdf online free, "
        "pdf converter no email, pdf converter no registration, "
        "pdf converter unlimited, pdf converter no watermark, "
        "pdf converter fast, pdf converter safe, pdf converter free, "
        "pdf tools help, pdf conversion questions, pdf editing questions, "
        "pdf organization questions, pdf security questions"
    )

    faq_q1 = _("How do I convert PDF to Word?")
    faq_a1 = _(
        "To convert PDF to Word, simply upload your PDF file using the upload button "
        "or drag and drop it into the upload zone. Click the convert button and wait "
        "for the conversion to complete. Download your converted Word document using "
        "the download button. The conversion is free and requires no registration."
    )

    faq_q2 = _("Is Convertica free to use?")
    faq_a2 = _(
        "Yes, Convertica is completely free to use. All PDF conversion, editing, "
        "and organization tools are available at no cost. There are no hidden fees, "
        "no registration required, and no file size limits on the free plan."
    )

    faq_q3 = _("What file formats does Convertica support?")
    faq_a3 = _(
        "Convertica supports PDF, Word (DOC, DOCX), JPG/JPEG, and Excel formats. "
        "You can convert between these formats, edit PDFs, organize pages, "
        "and protect your documents with passwords."
    )

    faq_q4 = _("How do I merge multiple PDF files?")
    faq_a4 = _(
        "To merge PDF files, go to the Merge PDF page, select multiple PDF files, "
        "arrange them in the desired order, and click merge. "
        "All selected files will be combined into a single PDF document."
    )

    faq_q5 = _("Is my data secure?")
    faq_a5 = _(
        "Yes, your data is secure. All files are processed securely and "
        "automatically deleted immediately after conversion. "
        "We do not store your files, and your privacy is our top priority. "
        "You can also protect your PDFs with password encryption."
    )

    context = {
        "page_title": page_title,
        "page_description": page_description,
        "page_keywords": page_keywords,
        "faq_q1": faq_q1,
        "faq_a1": faq_a1,
        "faq_q2": faq_q2,
        "faq_a2": faq_a2,
        "faq_q3": faq_q3,
        "faq_a3": faq_a3,
        "faq_q4": faq_q4,
        "faq_a4": faq_a4,
        "faq_q5": faq_q5,
        "faq_a5": faq_a5,
    }
    return render(request, "frontend/faq.html", context)


def _get_sitemap_base_url(request):
    """Get base URL for sitemap generation."""
    from decouple import config

    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    site_domain = config("SITE_DOMAIN", default=None)
    if site_domain:
        return f"{scheme}://{site_domain}"
    return f"{scheme}://{request.get_host()}"


def _get_sitemap_pages():
    """Get list of pages for sitemap."""
    return [
        {"url": "", "priority": "1.0", "changefreq": "daily"},
        {"url": "about/", "priority": "0.8", "changefreq": "monthly"},
        {"url": "privacy/", "priority": "0.6", "changefreq": "yearly"},
        {"url": "terms/", "priority": "0.6", "changefreq": "yearly"},
        {"url": "contact/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "faq/", "priority": "0.8", "changefreq": "monthly"},
        {"url": "pricing/", "priority": "0.8", "changefreq": "monthly"},
        {"url": "contribute/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "all-tools/", "priority": "0.9", "changefreq": "weekly"},
        {"url": "premium-tools/", "priority": "0.7", "changefreq": "weekly"},
        {"url": "epub-to-pdf/", "priority": "0.6", "changefreq": "monthly"},
        {"url": "pdf-to-epub/", "priority": "0.6", "changefreq": "monthly"},
        {"url": "pdf-to-markdown/", "priority": "0.6", "changefreq": "monthly"},
        {"url": "compare-pdf/", "priority": "0.6", "changefreq": "monthly"},
        {"url": "blog/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-to-word/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "word-to-pdf/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-to-jpg/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "jpg-to-pdf/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-to-excel/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "excel-to-pdf/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "ppt-to-pdf/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "html-to-pdf/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-to-ppt/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-to-html/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-edit/rotate/", "priority": "0.8", "changefreq": "weekly"},
        {
            "url": "pdf-edit/add-page-numbers/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {"url": "pdf-edit/add-watermark/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-edit/crop/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-organize/merge/", "priority": "0.9", "changefreq": "weekly"},
        {"url": "pdf-organize/split/", "priority": "0.8", "changefreq": "weekly"},
        {
            "url": "pdf-organize/remove-pages/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "url": "pdf-organize/extract-pages/",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {"url": "pdf-organize/organize/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-organize/compress/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "pdf-security/protect/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-security/unlock/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-to-text/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-edit/flatten/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "pdf-edit/sign/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "image/optimize/", "priority": "0.7", "changefreq": "monthly"},
        {"url": "image/convert/", "priority": "0.7", "changefreq": "monthly"},
        # NOTE: scanned-pdf-to-word/ and batch-converter/ are premium-gated and
        # 302-redirect anonymous crawlers to /users/login/. Keeping them out of
        # sitemap until they get public landing pages.
    ]


def sitemap_index(request):
    """Generate sitemap index pointing to language-specific sitemaps."""

    from django.core.cache import cache

    cache_key = "sitemap_index_v2"
    cached = cache.get(cache_key)
    if cached:
        return HttpResponse(cached, content_type="application/xml; charset=utf-8")

    base_url = _get_sitemap_base_url(request)
    current_date = datetime.now().strftime("%Y-%m-%d")
    languages = getattr(settings, "LANGUAGES", [("en", "English")])

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for lang_code, _ in languages:
        xml += "  <sitemap>\n"
        xml += f"    <loc>{base_url}/sitemap-{lang_code}.xml</loc>\n"
        xml += f"    <lastmod>{current_date}</lastmod>\n"
        xml += "  </sitemap>\n"

    xml += "</sitemapindex>"

    cache.set(cache_key, xml, 86400)
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def sitemap_lang(request, lang: str):
    """Generate sitemap for a specific language with hreflang annotations."""

    from django.core.cache import cache
    from django.utils.translation import activate, get_language
    from src.blog.models import Article

    languages = getattr(settings, "LANGUAGES", [("en", "English")])
    lang_codes = [code for code, _ in languages]

    if lang not in lang_codes:
        from django.http import Http404

        raise Http404("Invalid language")

    cache_key = f"sitemap_{lang}_v2"
    cached = cache.get(cache_key)
    if cached:
        return HttpResponse(cached, content_type="application/xml; charset=utf-8")

    base_url = _get_sitemap_base_url(request)
    current_date = datetime.now().strftime("%Y-%m-%d")
    default_language = settings.LANGUAGE_CODE
    old_lang = get_language()
    pages = _get_sitemap_pages()

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'

    for page in pages:
        page_url = page["url"]
        url = (
            f"{base_url}/{lang}/" if page_url == "" else f"{base_url}/{lang}/{page_url}"
        )

        xml += "  <url>\n"
        xml += f"    <loc>{url}</loc>\n"
        xml += f"    <lastmod>{current_date}</lastmod>\n"
        xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{page["priority"]}</priority>\n'

        for alt_lang_code, _ in languages:
            alt_url = (
                f"{base_url}/{alt_lang_code}/"
                if page_url == ""
                else f"{base_url}/{alt_lang_code}/{page_url}"
            )
            xml += (
                f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" href="{alt_url}"/>'
                + "\n"
            )

        default_url = (
            f"{base_url}/{default_language}/"
            if page_url == ""
            else f"{base_url}/{default_language}/{page_url}"
        )
        xml += (
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_url}"/>'
            + "\n"
        )
        xml += "  </url>\n"

    published_articles = (
        Article.objects.filter(status="published")
        .only("slug", "updated_at")
        .order_by("-published_at")
    )

    for article in published_articles:
        lastmod = (
            article.updated_at.strftime("%Y-%m-%d")
            if article.updated_at
            else current_date
        )

        activate(lang)
        try:
            article_url = article.get_absolute_url()
            if isinstance(article_url, bytes):
                article_url = article_url.decode("utf-8")
        except Exception:
            article_url = f"/{lang}/blog/{article.slug}/"

        full_url = f"{base_url}{article_url}"

        xml += "  <url>\n"
        xml += f"    <loc>{full_url}</loc>\n"
        xml += f"    <lastmod>{lastmod}</lastmod>\n"
        xml += "    <changefreq>monthly</changefreq>\n"
        xml += "    <priority>0.7</priority>\n"

        for alt_lang_code, _ in languages:
            activate(alt_lang_code)
            try:
                alt_url = article.get_absolute_url()
                if isinstance(alt_url, bytes):
                    alt_url = alt_url.decode("utf-8")
            except Exception:
                alt_url = f"/{alt_lang_code}/blog/{article.slug}/"
            xml += f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" href="{base_url}{alt_url}"/>\n'

        activate(default_language)
        try:
            default_url = article.get_absolute_url()
            if isinstance(default_url, bytes):
                default_url = default_url.decode("utf-8")
        except Exception:
            default_url = f"/{default_language}/blog/{article.slug}/"
        xml += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{base_url}{default_url}"/>\n'

        xml += "  </url>\n"

    # Blog pagination pages: /<lang>/blog/?page=2..N. Each page is self-canonical
    # (per test_blog_pagination_keeps_indexable_self_canonical) and indexable.
    # Without sitemap entries Ahrefs flags them as "Indexable page not in sitemap".
    # Page size mirrors Paginator(articles, 9) in src/blog/views.py:article_list.
    blog_page_size = 9
    total_published = published_articles.count()
    blog_total_pages = (
        (total_published + blog_page_size - 1) // blog_page_size
        if total_published
        else 0
    )
    for page_num in range(2, blog_total_pages + 1):
        page_loc = f"{base_url}/{lang}/blog/?page={page_num}"
        xml += "  <url>\n"
        xml += f"    <loc>{page_loc}</loc>\n"
        xml += f"    <lastmod>{current_date}</lastmod>\n"
        xml += "    <changefreq>weekly</changefreq>\n"
        xml += "    <priority>0.6</priority>\n"
        for alt_lang_code, _ in languages:
            alt_page_url = f"{base_url}/{alt_lang_code}/blog/?page={page_num}"
            xml += (
                f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" '
                f'href="{alt_page_url}"/>\n'
            )
        default_page_url = f"{base_url}/{default_language}/blog/?page={page_num}"
        xml += (
            f'    <xhtml:link rel="alternate" hreflang="x-default" '
            f'href="{default_page_url}"/>\n'
        )
        xml += "  </url>\n"

    activate(old_lang)
    xml += "</urlset>"

    cache.set(cache_key, xml, 86400)
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def sitemap_xml(request):
    """Legacy sitemap.xml - redirects to sitemap index."""
    return sitemap_index(request)


class PricingPageView(TemplateView):
    """Pricing page for Convertica Premium with all plans and Heroes Hall."""

    template_name = "frontend/pricing.html"

    def get_context_data(self, **kwargs):
        from src.users.models import SubscriptionPlan, User

        context = super().get_context_data(**kwargs)

        # Add Heroes Hall and top subscribers
        context["heroes"] = User.get_heroes()
        context["top_subscribers"] = User.get_top_subscribers(10)

        plans = (
            SubscriptionPlan.objects.filter(
                slug__in=["monthly-hero", "yearly-hero"],
                is_active=True,
            )
            .only("slug", "price", "currency", "duration_days")
            .all()
        )
        plans_by_slug = {p.slug: p for p in plans}

        context["monthly_plan"] = plans_by_slug.get("monthly-hero")
        context["yearly_plan"] = plans_by_slug.get("yearly-hero")

        # Add Stripe publishable key for checkout
        if bool(getattr(settings, "PAYMENTS_ENABLED", True)):
            context["stripe_publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        else:
            context["stripe_publishable_key"] = ""

        return context


class SupportPageView(TemplateView):
    template_name = "frontend/support.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Contribute to Convertica")
        context["page_description"] = _(
            "Contribute to the Convertica project with a one-time or monthly donation. "
            "This does not unlock Premium features — it simply helps development. "
            "Heroes are Premium subscribers; contributions here are support only."
        )
        context["page_keywords"] = (
            "convertica contribute, donate, contribution, support project"
        )
        return context


class SupportSuccessPageView(TemplateView):
    template_name = "frontend/support_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Thank you for your contribution")
        context["page_description"] = _(
            "Thank you for contributing to Convertica. Your support helps us keep improving the service."
        )
        context["page_keywords"] = "convertica contribute success, thank you"
        return context
