# utils_site/src/frontend/views.py

from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import TemplateView


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
    }

    # Define related tools for each tool
    relations = {
        "pdf_to_word": ["word_to_pdf", "pdf_to_excel", "merge_pdf"],
        "word_to_pdf": ["pdf_to_word", "merge_pdf", "compress_pdf"],
        "pdf_to_jpg": ["jpg_to_pdf", "compress_pdf", "split_pdf"],
        "jpg_to_pdf": ["pdf_to_jpg", "merge_pdf", "compress_pdf"],
        "rotate_pdf": ["organize_pdf", "compress_pdf", "merge_pdf"],
        "add_page_numbers": ["rotate_pdf", "organize_pdf", "merge_pdf"],
        "add_watermark": ["protect_pdf", "compress_pdf", "merge_pdf"],
        "crop_pdf": ["rotate_pdf", "compress_pdf", "organize_pdf"],
        "merge_pdf": ["split_pdf", "compress_pdf", "organize_pdf"],
        "split_pdf": ["merge_pdf", "compress_pdf", "organize_pdf"],
        "remove_pages": ["split_pdf", "organize_pdf", "merge_pdf"],
        "extract_pages": ["split_pdf", "merge_pdf", "organize_pdf"],
        "organize_pdf": ["merge_pdf", "split_pdf", "rotate_pdf"],
        "pdf_to_excel": ["pdf_to_word", "merge_pdf", "compress_pdf"],
        "excel_to_pdf": ["pdf_to_excel", "merge_pdf", "compress_pdf"],
        "ppt_to_pdf": ["merge_pdf", "compress_pdf", "protect_pdf"],
        "html_to_pdf": ["merge_pdf", "compress_pdf", "protect_pdf"],
        "pdf_to_ppt": ["merge_pdf", "compress_pdf", "split_pdf"],
        "pdf_to_html": ["pdf_to_word", "compress_pdf", "split_pdf"],
        "compress_pdf": ["merge_pdf", "split_pdf", "protect_pdf"],
        "protect_pdf": ["unlock_pdf", "compress_pdf", "merge_pdf"],
        "unlock_pdf": ["protect_pdf", "compress_pdf", "merge_pdf"],
    }

    related_keys = relations.get(current_tool, [])
    result = []
    for key in related_keys:
        if key in all_tools:
            tool = all_tools[key].copy()
            tool["url"] = reverse(tool["url"])
            result.append(tool)
    return result


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
        if api_url_name == "excel_to_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("excel_to_pdf_batch_api")
            batch_field_name = "excel_files"
        elif api_url_name == "ppt_to_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("ppt_to_pdf_batch_api")
            batch_field_name = "ppt_files"
        elif api_url_name == "pdf_to_word_api":
            batch_enabled = True
            batch_api_url = reverse("pdf_to_word_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "word_to_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("word_to_pdf_batch_api")
            batch_field_name = "word_files"
        elif api_url_name == "pdf_to_jpg_api":
            batch_enabled = True
            batch_api_url = reverse("pdf_to_jpg_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "jpg_to_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("jpg_to_pdf_batch_api")
            batch_field_name = "image_files"
        elif api_url_name == "pdf_to_excel_api":
            batch_enabled = True
            batch_api_url = reverse("pdf_to_excel_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "pdf_to_ppt_api":
            batch_enabled = True
            batch_api_url = reverse("pdf_to_ppt_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "pdf_to_html_api":
            batch_enabled = True
            batch_api_url = reverse("pdf_to_html_batch_api")
            batch_field_name = "pdf_files"

        elif api_url_name == "crop_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("crop_pdf_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "add_watermark_api":
            batch_enabled = True
            batch_api_url = reverse("add_watermark_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "add_page_numbers_api":
            batch_enabled = True
            batch_api_url = reverse("add_page_numbers_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "compress_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("compress_pdf_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "split_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("split_pdf_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "extract_pages_api":
            batch_enabled = True
            batch_api_url = reverse("extract_pages_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "remove_pages_api":
            batch_enabled = True
            batch_api_url = reverse("remove_pages_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "organize_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("organize_pdf_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "protect_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("protect_pdf_batch_api")
            batch_field_name = "pdf_files"
        elif api_url_name == "unlock_pdf_api":
            batch_enabled = True
            batch_api_url = reverse("unlock_pdf_batch_api")
            batch_field_name = "pdf_files"

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
    }


def pdf_to_word_page(request):
    """PDF to Word conversion page."""
    context = _get_converter_context(
        request,
        page_title=_(
            "PDF to Word Converter Online Free - No Registration | Convertica"
        ),
        page_description=_(
            "Convert PDF to Word online free without losing formatting. "
            "Preserve tables, images & fonts. No registration, no watermark. "
            "Works on Windows, Mac, Linux, iOS, Android. Try now!"
        ),
        page_keywords=(
            # Primary keywords
            "PDF to Word, convert PDF to Word online free, PDF to DOCX, PDF to Word converter, "
            "convert PDF to Word without losing formatting, PDF to Word no email required, "
            # Feature-based keywords
            "pdf to word keep tables, pdf to word preserve formatting, pdf to word keep images, "
            "pdf to word maintain layout, pdf to word editable, pdf to word searchable, "
            # Use case keywords
            "pdf to word for resume, pdf to word for cv, pdf to word for contract, "
            "pdf to word for invoice, pdf to word for legal documents, pdf to word for thesis, "
            "pdf to word academic paper, pdf to word job application, pdf to word university, "
            # Platform keywords
            "pdf to word mac, pdf to word windows, pdf to word linux, pdf to word chromebook, "
            "pdf to word iphone, pdf to word android, pdf to word mobile, pdf to word tablet, "
            # Quality keywords
            "pdf to word high quality, pdf to word best 2026, pdf to word accurate, "
            "pdf to word clean layout, pdf to word high accuracy, pdf to word no errors, "
            # Free/No registration keywords
            "pdf to word free, pdf to word no registration, pdf to word no sign up, "
            "pdf to word no watermark, pdf to word unlimited, pdf to word safe, "
            # OCR keywords
            "convert scanned pdf to word, pdf to word ocr, scanned image pdf to docx, "
            "pdf to word extract text, best ocr pdf to word free, "
            # Comparison keywords
            "smallpdf alternative, ilovepdf alternative, adobe acrobat alternative"
        ),
        page_subtitle=_(
            "Convert your PDF documents to editable Word format in seconds"
        ),
        header_text=_("PDF to Word Converter"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_word_api",
        replace_regex=r"\.pdf$",
        replace_to=".docx",
        button_text=_("Convert PDF to Word"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Preserve Formatting"),
            "description": _(
                "Tables, images, fonts, and layout stay intact after conversion"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("100% Free & Secure"),
            "description": _(
                "No registration, no watermarks. Files deleted immediately after conversion"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Works on All Devices"),
            "description": _(
                "Convert PDF to Word on Windows, Mac, Linux, iOS, Android"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
            "gradient": "from-amber-500 to-orange-600",
            "title": _("OCR for Scanned PDFs"),
            "description": _(
                "Premium: Convert image-based PDFs to editable text with 15+ languages"
            ),
        },
    ]
    context["benefits_title"] = _("Why Convert PDF to Word with Convertica?")

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("Can I convert a scanned PDF to Word?"),
            "answer": _(
                "Yes! Premium users can enable OCR (Optical Character Recognition) to convert "
                "scanned PDFs and image-based documents to editable Word format. "
                "OCR supports 15+ languages including English, Russian, German, French, "
                "Spanish, Chinese, Japanese, and Arabic for accurate text recognition."
            ),
        },
        {
            "question": _("Will my tables and formatting be preserved?"),
            "answer": _(
                "Yes, our PDF to Word converter preserves tables, images, fonts, headers, "
                "footers, and complex layouts. The converted Word document will look "
                "as close to the original PDF as possible, maintaining text alignment "
                "and paragraph spacing."
            ),
        },
        {
            "question": _("Is this PDF to Word converter really free?"),
            "answer": _(
                "Yes, Convertica PDF to Word converter is completely free for standard use. "
                "No registration required, no email needed, no watermarks added. "
                "Premium subscription is optional and provides higher page limits and OCR features."
            ),
        },
        {
            "question": _("What is the maximum file size I can convert?"),
            "answer": _(
                "Free users can convert PDF files up to 50 pages. "
                "For larger documents, you can split them first using our Split PDF tool, "
                "or upgrade to Premium for higher limits up to 500 pages per file."
            ),
        },
        {
            "question": _("Can I convert PDF to Word on my phone?"),
            "answer": _(
                "Yes! Convertica works on all mobile devices - iPhone, iPad, Android phones "
                "and tablets. Simply open the website in your mobile browser, upload your PDF, "
                "and download the converted Word document. No app installation required."
            ),
        },
    ]
    context["faq_title"] = _("PDF to Word Converter - FAQ")

    # SEO Tips
    context["page_tips"] = [
        _(
            "Text-based PDFs convert better than scanned documents - for scanned PDFs, enable OCR"
        ),
        _(
            "For best results, use PDFs created from Word or other text editors, not screenshots"
        ),
        _(
            "Large files (over 50 pages) may take longer - consider splitting them first"
        ),
        _(
            "If tables look misaligned, try re-saving the original PDF before converting"
        ),
        _("After conversion, review formatting in Word and adjust if needed"),
    ]
    context["tips_title"] = _("Tips for Best PDF to Word Conversion")

    # SEO Content
    context["page_content_title"] = _("Convert PDF to Word Online - Fast & Accurate")
    context["page_content_body"] = _(
        "<p>Need to edit a PDF document? Our <strong>free PDF to Word converter</strong> "
        "transforms your PDF files into fully editable Word documents (.docx) while "
        "preserving the original formatting, including tables, images, fonts, and layout.</p>"
        "<p>Whether you're converting a <strong>resume, contract, invoice, or academic paper</strong>, "
        "Convertica ensures high-quality PDF to DOCX conversion. Unlike other tools, we maintain "
        "complex formatting elements like multi-column layouts, headers, footers, and embedded graphics.</p>"
        "<p><strong>For scanned PDFs:</strong> Premium users can enable OCR (Optical Character "
        "Recognition) to extract text from image-based PDFs. Our OCR supports 15+ languages "
        "including English, Russian, German, French, Spanish, Chinese, Japanese, and Arabic.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("pdf_to_word")

    return render(request, "frontend/pdf_convert/pdf_to_word.html", context)


def word_to_pdf_page(request):
    """Word to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_(
            "Word to PDF Converter Free Online - Convert DOCX to PDF | Convertica"
        ),
        page_description=_(
            "Convert Word to PDF online free without losing formatting. "
            "Preserve fonts, images & layout. No registration, no watermark. "
            "Works on all devices. Fast & secure conversion."
        ),
        page_keywords=(
            # Primary keywords
            "Word to PDF, DOCX to PDF, DOC to PDF, convert Word to PDF online free, "
            "word to pdf without losing formatting, docx to pdf converter, "
            # Feature-based keywords
            "word to pdf keep fonts, word to pdf preserve layout, word to pdf keep images, "
            "word to pdf maintain formatting, word to pdf high quality, word to pdf export, "
            # Use case keywords
            "convert resume to pdf, word to pdf for cv, word to pdf for contract, "
            "word to pdf for invoice, word to pdf for legal documents, word to pdf for thesis, "
            "word to pdf academic paper, word to pdf job application, word to pdf business, "
            # Platform keywords
            "word to pdf mac, word to pdf windows, word to pdf linux, word to pdf online, "
            "word to pdf iphone, word to pdf android, word to pdf mobile, word to pdf chromebook, "
            # Free/No registration keywords
            "word to pdf free, word to pdf no registration, word to pdf no sign up, "
            "word to pdf no watermark, word to pdf unlimited, word to pdf safe, word to pdf secure, "
            # Batch/Multiple files keywords
            "word to pdf batch converter, convert multiple word to pdf, word to pdf bulk, "
            # Quality keywords
            "word to pdf best 2026, word to pdf fast online, word to pdf one click, "
            "word to pdf clean, word to pdf professional"
        ),
        page_subtitle=_("Convert your Word documents to PDF format in seconds"),
        header_text=_("Word to PDF Converter"),
        file_input_name="word_file",
        file_accept=".doc,.docx",
        api_url_name="word_to_pdf_api",
        replace_regex=r"\.(docx?|DOCX?)$",
        replace_to=".pdf",
        button_text=_("Convert to PDF"),
        select_file_message=_("Please select a Word file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Perfect Formatting"),
            "description": _(
                "Fonts, images, tables, and layout are preserved exactly as in your Word document"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Secure & Private"),
            "description": _(
                "Files are encrypted and automatically deleted. Your documents stay private"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Fast Conversion"),
            "description": _(
                "Convert Word to PDF in seconds. No waiting, instant download"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-amber-500 to-orange-600",
            "title": _("Universal Format"),
            "description": _(
                "PDF works everywhere - share documents that look the same on any device"
            ),
        },
    ]
    context["benefits_title"] = _("Why Convert Word to PDF with Convertica?")

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("Will my fonts be preserved in the PDF?"),
            "answer": _(
                "Yes! Our Word to PDF converter embeds fonts in the PDF, ensuring your document "
                "looks exactly the same on any device. This includes custom fonts, special characters, "
                "and text formatting like bold, italic, and underline."
            ),
        },
        {
            "question": _("Can I convert multiple Word files at once?"),
            "answer": _(
                "Premium users can use batch conversion to convert multiple Word documents to PDF "
                "in one go. Simply select all your files and convert them simultaneously. "
                "Free users can convert files one at a time."
            ),
        },
        {
            "question": _("Is the conversion free and without watermark?"),
            "answer": _(
                "Yes, Convertica Word to PDF converter is completely free. We never add watermarks "
                "to your converted PDFs. No registration required, no email needed. "
                "Premium subscription is optional for higher limits and batch conversion."
            ),
        },
        {
            "question": _("Does the converter support DOC and DOCX formats?"),
            "answer": _(
                "Yes, we support both older DOC format (Word 97-2003) and modern DOCX format "
                "(Word 2007 and later). Simply upload your file and we'll convert it to PDF "
                "regardless of the Word version used to create it."
            ),
        },
        {
            "question": _("Can I convert Word to PDF on my phone?"),
            "answer": _(
                "Yes! Convertica works on all mobile devices including iPhone, iPad, and Android. "
                "Open our website in your mobile browser, upload your Word document, "
                "and download the PDF. No app installation needed."
            ),
        },
    ]
    context["faq_title"] = _("Word to PDF Converter - FAQ")

    # SEO Tips
    context["page_tips"] = [
        _("For best results, use documents created in Microsoft Word or Google Docs"),
        _("Check that all fonts are properly installed before converting"),
        _("Large documents with many images may take longer to convert"),
        _(
            "If hyperlinks don't work in PDF, ensure they were active in the Word document"
        ),
        _("Use 'Print Layout' view in Word to preview how the PDF will look"),
    ]
    context["tips_title"] = _("Tips for Best Word to PDF Conversion")

    # SEO Content
    context["page_content_title"] = _("Convert Word to PDF Online - Fast & Reliable")
    context["page_content_body"] = _(
        "<p>Need to share a Word document that looks perfect on any device? Our <strong>free Word to PDF "
        "converter</strong> transforms your DOCX and DOC files into professional PDF documents while "
        "preserving all formatting, fonts, images, and layout.</p>"
        "<p>PDF is the universal standard for document sharing - your <strong>resume, contract, report, "
        "or thesis</strong> will look exactly the same whether opened on Windows, Mac, Linux, or mobile devices. "
        "Recipients don't need Microsoft Word to view your documents.</p>"
        "<p><strong>Perfect for professionals:</strong> Convert Word documents to PDF for email attachments, "
        "online submissions, printing, and archiving. All hyperlinks, bookmarks, and table of contents "
        "are preserved in the converted PDF.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("word_to_pdf")
    return render(request, "frontend/pdf_convert/word_to_pdf.html", context)


def pdf_to_jpg_page(request):
    """PDF to JPG conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to JPG Online Free - Convert PDF to Images | Convertica"),
        page_description=_(
            "Convert PDF to JPG online free with high quality. "
            "PDF to image converter with no watermark, high resolution (300-600 DPI), "
            "batch conversion. Extract images from PDF or convert PDF pages to JPG/PNG. "
            "Perfect for printing, web upload, and social media."
        ),
        page_keywords=(
            # Primary keywords
            "PDF to JPG, PDF to image, convert PDF to JPG, pdf to jpg online free, "
            "pdf to image converter, PDF to JPG converter, "
            # Quality keywords
            "pdf to png converter high quality, pdf to image no watermark, "
            "pdf to jpg high resolution, pdf to jpg without losing quality, "
            "pdf to jpg best quality online, pdf to jpg hd converter, "
            # DPI/resolution keywords
            "pdf to image converter 300 dpi, 600 dpi pdf to jpg converter, "
            "pdf to jpg high dpi, pdf to image high resolution, "
            # Batch/multiple keywords
            "batch pdf to jpg converter, pdf to jpg convert all pages, "
            "convert multiple pdf pages to jpg, pdf to jpg bulk converter, "
            # Use case keywords
            "pdf to jpg for printing, pdf to jpg for website upload, "
            "pdf to image for instagram, pdf to image for social media, "
            "pdf to jpg for presentation, pdf poster to jpg, "
            # Format keywords
            "pdf to png converter, pdf to jpeg converter, "
            "export pdf pages as images, extract images from pdf, "
            # Platform keywords
            "pdf to jpg converter for mac online, pdf to jpg online mac, "
            "pdf to jpg converter windows, pdf to jpg mobile, "
            # Free/no registration keywords
            "pdf to jpg converter no ads, pdf to jpg unlimited free, "
            "convert pdf to jpg free no registration, pdf to jpg no signup"
        ),
        page_subtitle=_("Convert PDF pages to high-quality JPG images in seconds"),
        header_text=_("PDF to JPG Converter"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_jpg_api",
        replace_regex=r"\.pdf$",
        replace_to=".zip",
        button_text=_("Convert PDF to JPG"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("High Quality Images"),
            "description": _(
                "Convert PDF to JPG with up to 600 DPI resolution for crisp, clear images"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Batch Conversion"),
            "description": _(
                "Convert all PDF pages to images at once and download as ZIP archive"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("No Watermark"),
            "description": _(
                "Get clean images without any watermarks or branding on your converted files"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Fast Processing"),
            "description": _(
                "Lightning-fast conversion with instant download - no waiting time"
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a PDF to JPG?"),
            "answer": _(
                "Simply upload your PDF file, click the Convert button, and download your JPG images. "
                "All pages will be converted to separate high-quality JPG files and packaged in a ZIP archive."
            ),
        },
        {
            "question": _("What resolution are the converted JPG images?"),
            "answer": _(
                "Our converter produces high-resolution images at 300 DPI by default, which is perfect for "
                "printing and professional use. The quality is preserved during conversion."
            ),
        },
        {
            "question": _("Can I convert a multi-page PDF to JPG?"),
            "answer": _(
                "Yes! When you convert a multi-page PDF, each page becomes a separate JPG image. "
                "All images are packaged in a convenient ZIP file for easy download."
            ),
        },
        {
            "question": _("Is there a limit on PDF file size?"),
            "answer": _(
                "Free users can convert PDFs with up to a certain number of pages. "
                "For larger files, you can split them into smaller parts or upgrade to Premium for higher limits."
            ),
        },
        {
            "question": _("Are my PDF files secure?"),
            "answer": _(
                "Yes, your files are processed securely and automatically deleted after conversion. "
                "We don't store or share your documents. Your privacy is our priority."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use high-quality source PDFs for best image results"),
        _("For printing, ensure your PDF has at least 300 DPI resolution"),
        _("Convert vector-based PDFs for crisp text and graphics"),
        _("For web use, JPG format offers good compression with acceptable quality"),
        _("Download images as ZIP to keep all pages organized"),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "PDF to JPG Converter - Extract Images from PDF Online"
    )
    context["page_content_body"] = _(
        "<p>Our free PDF to JPG converter transforms your PDF documents into high-quality JPG images "
        "with just a few clicks. Whether you need images for presentations, social media, websites, "
        "or printing, our tool delivers crystal-clear results.</p>"
        "<p>The converter preserves the original quality of your PDF content, producing sharp images "
        "suitable for any purpose. Each page of your PDF becomes a separate JPG file, making it easy "
        "to use individual pages wherever you need them.</p>"
        "<p>Perfect for extracting images from PDF documents, creating thumbnails, preparing content "
        "for social media, or converting PDF presentations into image slides.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("pdf_to_jpg")
    return render(request, "frontend/pdf_convert/pdf_to_jpg.html", context)


def jpg_to_pdf_page(request):
    """JPG to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("JPG to PDF Online Free - Convert Images to PDF | Convertica"),
        page_description=_(
            "Convert JPG to PDF online free without compression. "
            "Merge multiple images into one PDF, combine photos to PDF, "
            "create PDF from images with high resolution. "
            "Perfect for documents, receipts, homework, and university submissions. "
            "No watermark, unlimited conversions."
        ),
        page_keywords=(
            # Primary keywords
            "JPG to PDF, image to PDF, convert JPG to PDF, jpg to pdf online free, "
            "image to pdf converter, photo to PDF, "
            # Quality keywords
            "jpg to pdf without compression, jpg to pdf high quality, "
            "jpg to pdf no watermark, jpg to pdf sharp quality, "
            # Multiple images keywords
            "jpg to pdf merge multiple images, combine images into one pdf, "
            "combine photos to pdf online, multiple images to one pdf, "
            # Use case keywords
            "jpg to pdf for homework, jpg to pdf for university submission, "
            "convert scanned photos to pdf, image to pdf converter for receipts, "
            "convert screenshots to pdf, convert documents to pdf, "
            # Format keywords
            "png to pdf converter, jpeg to pdf, image to pdf, "
            "jpg to pdf for a4 format, photos to pdf, "
            # Platform keywords
            "jpg to pdf converter mac, jpg to pdf online mac, "
            "jpg to pdf converter windows, jpg to pdf mobile, "
            # Free/no registration keywords
            "jpg to pdf converter no ads, jpg to pdf unlimited free, "
            "jpg to pdf free no registration, jpg to pdf no signup"
        ),
        page_subtitle=_("Convert your JPG images to PDF format in seconds"),
        header_text=_("JPG to PDF Converter"),
        file_input_name="image_file",
        file_accept=".jpg,.jpeg",
        api_url_name="jpg_to_pdf_api",
        replace_regex=r"\.(jpg|jpeg|JPG|JPEG)$",
        replace_to=".pdf",
        button_text=_("Convert to PDF"),
        select_file_message=_("Please select a JPG/JPEG image file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("No Quality Loss"),
            "description": _(
                "Convert JPG to PDF without compression - your images stay crystal clear"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Multiple Image Support"),
            "description": _(
                "Upload multiple JPG images and combine them into a single PDF document"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Universal Format"),
            "description": _(
                "PDF works everywhere - share documents easily with anyone"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Conversion"),
            "description": _("Fast processing - convert your images to PDF in seconds"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a JPG image to PDF?"),
            "answer": _(
                "Simply upload your JPG image file, click the Convert button, and download your PDF. "
                "The conversion happens instantly with no quality loss."
            ),
        },
        {
            "question": _("Can I convert multiple JPG images to one PDF?"),
            "answer": _(
                "Yes! You can upload multiple JPG images and combine them into a single PDF document. "
                "Each image will become a separate page in the resulting PDF."
            ),
        },
        {
            "question": _("Is the image quality preserved during conversion?"),
            "answer": _(
                "Yes, our converter preserves the original quality of your JPG images. "
                "There is no compression applied during conversion, ensuring your images look exactly the same in the PDF."
            ),
        },
        {
            "question": _("What image formats are supported?"),
            "answer": _(
                "This converter supports JPG and JPEG image formats. For PNG images, "
                "please use our PNG to PDF converter or convert your PNG to JPG first."
            ),
        },
        {
            "question": _("Is there a file size limit?"),
            "answer": _(
                "Free users can convert images up to a certain size. For larger files, "
                "you may need to resize your images or upgrade to Premium for higher limits."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use high-resolution images for best PDF quality"),
        _("Ensure proper orientation before uploading for correct page layout"),
        _("For documents, scan at 300 DPI or higher for clear text"),
        _("Crop images before conversion to remove unwanted borders"),
        _("Name your images in order (1.jpg, 2.jpg) for easy organization"),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "JPG to PDF Converter - Create PDF from Images Online"
    )
    context["page_content_body"] = _(
        "<p>Our free JPG to PDF converter transforms your images into professional PDF documents "
        "with just one click. Perfect for creating digital portfolios, converting scanned documents, "
        "preparing homework submissions, or archiving photos.</p>"
        "<p>The converter maintains the original image quality - no compression means your photos "
        "and documents look exactly as intended. Each JPG image becomes a full page in the PDF, "
        "making it easy to create multi-page documents from your image collection.</p>"
        "<p>Ideal for students submitting assignments, professionals preparing reports, "
        "photographers creating portfolios, and anyone who needs to share images in PDF format.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("jpg_to_pdf")
    return render(request, "frontend/pdf_convert/jpg_to_pdf.html", context)


def rotate_pdf_page(request):
    """Rotate PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Rotate PDF - Convertica"),
        page_description=_(
            "Rotate PDF pages online free by 90, 180, or 270 degrees. "
            "Fast PDF rotation tool with no watermark, batch rotation, "
            "and quality preservation. Perfect for scanned documents and "
            "misoriented pages. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "rotate PDF, PDF rotation, rotate pdf online free, "
            "rotate pdf pages, pdf rotation tool, "
            # Angle keywords
            "rotate pdf pages 90 degrees, rotate pdf pages 180 degrees, "
            "rotate pdf pages 270 degrees, rotate pdf clockwise, "
            "rotate pdf counterclockwise, rotate pdf upside down, "
            # Use case keywords
            "rotate scanned pdf, fix pdf orientation, "
            "rotate pdf for printing, correct pdf page orientation, "
            "rotate pdf document, rotate pdf for mobile, "
            # Quality keywords
            "rotate pdf without losing quality, rotate pdf no watermark, "
            "pdf rotation maintain quality, rotate pdf high quality, "
            # Platform keywords
            "pdf rotation for mac online, rotate pdf windows, "
            "rotate pdf mobile, rotate pdf android, rotate pdf iphone, "
            # Free keywords
            "rotate pdf free no registration, rotate pdf no ads, "
            "rotate pdf unlimited, rotate pdf one click"
        ),
        page_subtitle=_("Rotate your PDF pages in seconds"),
        header_text=_("Rotate PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="rotate_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Rotate PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Multiple Rotation Angles"),
            "description": _(
                "Rotate pages by 90°, 180°, or 270° - clockwise or counterclockwise"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Quality Preserved"),
            "description": _(
                "All content, formatting, and images stay intact after rotation"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Selective Rotation"),
            "description": _(
                "Rotate all pages, current page, or specify exact pages to rotate"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Processing"),
            "description": _(
                "Fast rotation with immediate download - no waiting required"
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I rotate a PDF page?"),
            "answer": _(
                "Upload your PDF file, select the rotation angle (90°, 180°, or 270°), "
                "choose which pages to rotate, and click the Rotate button. Your rotated PDF "
                "will be ready to download instantly."
            ),
        },
        {
            "question": _("Can I rotate specific pages in a PDF?"),
            "answer": _(
                "Yes! You can rotate all pages, just the current page, or specify exact page numbers. "
                "Use formats like '1,3,5' for individual pages or '1-5' for a range."
            ),
        },
        {
            "question": _("Will rotating affect the PDF quality?"),
            "answer": _(
                "No, our rotation tool preserves all content, formatting, images, and text quality. "
                "The rotation only changes the page orientation without any quality loss."
            ),
        },
        {
            "question": _("How do I fix a sideways scanned PDF?"),
            "answer": _(
                "Upload your scanned PDF, select 90° (clockwise) or 270° (counterclockwise) "
                "depending on how the document is oriented, and rotate it to fix the orientation."
            ),
        },
        {
            "question": _("Is there a limit on PDF file size?"),
            "answer": _(
                "Free users can rotate PDFs with up to a certain number of pages. "
                "For larger files, split them or upgrade to Premium for higher limits."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Preview your PDF before rotating to identify which pages need rotation"),
        _("Use 90° clockwise to rotate a landscape page to portrait"),
        _("Use 270° (counterclockwise) for the opposite direction"),
        _("Rotate specific pages if only some pages are misoriented"),
        _("Check the final PDF before downloading to ensure correct orientation"),
    ]

    # SEO Content
    context["page_content_title"] = _("Rotate PDF Pages Online - Fix PDF Orientation")
    context["page_content_body"] = _(
        "<p>Our free PDF rotation tool lets you quickly fix page orientation in any PDF document. "
        "Whether you have scanned documents that came out sideways, or pages that need to be "
        "turned upside down, our tool handles it all.</p>"
        "<p>Choose from 90°, 180°, or 270° rotation angles and apply them to all pages, "
        "just the current page, or specific pages you select. The rotation is instant and "
        "preserves all your content perfectly.</p>"
        "<p>Perfect for fixing scanned documents, rotating landscape pages to portrait, "
        "correcting improperly oriented PDFs, and preparing documents for printing or sharing.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("rotate_pdf")
    return render(request, "frontend/pdf_edit/rotate_pdf.html", context)


def add_page_numbers_page(request):
    """Add page numbers to PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Add Page Numbers to PDF Online Free | Convertica"),
        page_description=_(
            "Add page numbers to PDF online free with customizable position, "
            "font size, and format. Fast PDF page numbering tool with no watermark. "
            "Perfect for documents, reports, and academic papers. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "add page numbers PDF, PDF page numbers, add page numbers to pdf online free, "
            "number pdf pages, pdf page numbering tool, "
            # Position keywords
            "pdf page numbers top, pdf page numbers bottom, "
            "pdf page numbers center, pdf page numbers left, pdf page numbers right, "
            # Use case keywords
            "pdf page numbers for documents, pdf page numbers for reports, "
            "pdf page numbers for academic papers, pdf page numbers for thesis, "
            "pdf page numbering for invoices, pdf page numbers for legal documents, "
            # Feature keywords
            "pdf page numbers custom position, pdf page numbers font size, "
            "pdf page numbers format, add page numbers pdf batch, "
            # Quality keywords
            "add page numbers pdf no watermark, pdf page numbering maintain quality, "
            # Platform keywords
            "add page numbers pdf for mac online, add page numbers pdf for mobile, "
            # Free keywords
            "add page numbers pdf free, add page numbers pdf without registration"
        ),
        page_subtitle=_("Add page numbers to your PDF in seconds"),
        header_text=_("Add Page Numbers"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="add_page_numbers_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Add Page Numbers"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Customizable Position"),
            "description": _(
                "Place numbers at top, bottom, left, right, or center of pages"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Custom Formatting"),
            "description": _(
                "Choose font size, style, and number format to match your document"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Quality Preserved"),
            "description": _("Original PDF content and formatting remain unchanged"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Fast Processing"),
            "description": _("Add page numbers instantly to any PDF document"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I add page numbers to a PDF?"),
            "answer": _(
                "Upload your PDF file, choose where you want the numbers to appear "
                "(top, bottom, left, right, or center), customize the format if needed, "
                "and click the button. Your numbered PDF will be ready to download."
            ),
        },
        {
            "question": _("Can I choose where page numbers appear?"),
            "answer": _(
                "Yes! You can position page numbers at the top or bottom of the page, "
                "and align them to the left, center, or right. This gives you full control "
                "over the appearance of your document."
            ),
        },
        {
            "question": _("Will adding page numbers change my document content?"),
            "answer": _(
                "No, adding page numbers only adds the numbers to your pages. "
                "All existing content, formatting, images, and links remain unchanged."
            ),
        },
        {
            "question": _("Can I start numbering from a specific page?"),
            "answer": _(
                "Yes, you can customize the starting page number and choose which pages "
                "to number. This is useful for documents with title pages or table of contents."
            ),
        },
        {
            "question": _("What number formats are available?"),
            "answer": _(
                "You can use simple numbers (1, 2, 3), Roman numerals (i, ii, iii), "
                "or custom formats like 'Page 1 of N'. Choose the format that best fits your needs."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use bottom-center for most documents - it's the standard position"),
        _("For academic papers, check your institution's formatting requirements"),
        _("Skip the first page if it's a title page or cover"),
        _("Use a smaller font size for page numbers to keep them unobtrusive"),
        _("Preview your document to ensure numbers don't overlap with content"),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "Add Page Numbers to PDF - Professional Document Numbering"
    )
    context["page_content_body"] = _(
        "<p>Our free PDF page numbering tool makes it easy to add professional page numbers "
        "to any PDF document. Whether you're preparing a thesis, business report, contract, "
        "or any multi-page document, proper page numbering improves navigation and professionalism.</p>"
        "<p>Customize the position, font size, and format of your page numbers to match your "
        "document's style. You can place numbers at the top or bottom of pages, align them "
        "left, center, or right, and choose from various numbering formats.</p>"
        "<p>Ideal for academic papers, legal documents, business reports, manuals, "
        "and any document that benefits from clear page numbering.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("add_page_numbers")
    return render(request, "frontend/pdf_edit/add_page_numbers.html", context)


def add_watermark_page(request):
    """Add watermark to PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Add Watermark to PDF Online Free | Convertica"),
        page_description=_(
            "Add watermark to PDF online free with text or image. "
            "Customize position, transparency, and size. "
            "Fast PDF watermarking tool with no watermark on tool itself. "
            "Perfect for document protection and branding. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "add watermark PDF, PDF watermark, add watermark to pdf online free, "
            "watermark pdf documents, pdf watermarking tool, "
            # Type keywords
            "add text watermark to pdf, add image watermark to pdf, "
            "pdf watermark logo, pdf watermark text, "
            # Customization keywords
            "pdf watermark custom position, pdf watermark transparency, "
            "pdf watermark diagonal, pdf watermark center, "
            # Use case keywords
            "pdf watermark for documents, pdf watermark for protection, "
            "pdf watermark for branding, pdf watermark confidential, "
            # Platform keywords
            "add watermark pdf for mac online, add watermark pdf for mobile, "
            # Free keywords
            "add watermark pdf free, add watermark pdf without registration"
        ),
        page_subtitle=_("Add watermark to your PDF in seconds"),
        header_text=_("Add Watermark"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="add_watermark_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Add Watermark"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Text & Image Watermarks"),
            "description": _(
                "Add custom text or upload images as watermarks on your PDFs"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Full Customization"),
            "description": _("Control color, opacity, size, position, and rotation"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Visual Preview"),
            "description": _(
                "See exactly how your watermark will look before applying"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Document Protection"),
            "description": _("Protect your documents with visible watermarks"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I add a watermark to a PDF?"),
            "answer": _(
                "Upload your PDF, enter text or upload an image, customize appearance, "
                "position it using the visual editor, and click Add Watermark."
            ),
        },
        {
            "question": _("Can I add a logo image as a watermark?"),
            "answer": _(
                "Yes! Upload PNG or JPG images as watermarks. Perfect for company logos, "
                "stamps, or signatures."
            ),
        },
        {
            "question": _("How do I make the watermark semi-transparent?"),
            "answer": _(
                "Use the opacity slider to adjust transparency from 10% to 100%."
            ),
        },
        {
            "question": _("Can I add watermark to specific pages only?"),
            "answer": _(
                "Yes, apply to all pages, current page, or specify pages like '1,3,5' or '1-5'."
            ),
        },
        {
            "question": _("Will the watermark affect document quality?"),
            "answer": _(
                "No, watermarks are added as a layer on top of the original content. "
                "The underlying document quality remains unchanged. You can also remove "
                "watermarks later if needed."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use semi-transparent watermarks (30-50% opacity) for readability"),
        _("Position diagonal watermarks for document protection"),
        _("Use your company logo for professional branding"),
        _("Add 'CONFIDENTIAL' or 'DRAFT' text for document status"),
        _("Test your watermark on one page before applying to all pages"),
    ]

    # SEO Content
    context["page_content_title"] = _("Add Watermark to PDF - Protect Your Documents")
    context["page_content_body"] = _(
        "<p>Our free PDF watermark tool lets you add custom text or image watermarks. "
        "Protect your intellectual property, brand documents, or mark them as confidential.</p>"
        "<p>The visual editor shows exactly how your watermark will appear. "
        "Drag to position, adjust size and rotation - all with real-time preview.</p>"
        "<p><strong>Common uses:</strong> Add company logos for branding, mark documents as "
        "'DRAFT' or 'CONFIDENTIAL', add copyright notices, or include approval stamps "
        "and signatures on official documents.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("add_watermark")
    return render(request, "frontend/pdf_edit/add_watermark.html", context)


def crop_pdf_page(request):
    """Crop PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Crop PDF Online Free - Remove Margins | Convertica"),
        page_description=_(
            "Crop PDF pages online free with precise crop box coordinates. "
            "Fast PDF cropping tool with no watermark, visual editor, "
            "and quality preservation. Perfect for removing margins and "
            "unwanted content. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "crop PDF, PDF crop, crop pdf online free, "
            "crop pdf pages, pdf cropping tool, "
            # Feature keywords
            "crop pdf with visual editor, crop pdf precise coordinates, "
            "crop pdf remove margins, crop pdf unwanted content, "
            # Use case keywords
            "crop pdf for printing, crop pdf for scanning, "
            "crop pdf for documents, crop pdf trim margins, "
            # Quality keywords
            "crop pdf without losing quality, crop pdf maintain quality, "
            "pdf cropping no watermark, crop pdf high quality, "
            # Platform keywords
            "pdf cropping for mac online, pdf cropping for mobile, "
            # Free keywords
            "crop pdf free, crop pdf without registration"
        ),
        page_subtitle=_("Crop your PDF pages in seconds"),
        header_text=_("Crop PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="crop_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Crop PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Visual Crop Editor"),
            "description": _(
                "Select crop area visually by clicking and dragging on the PDF"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Quality Preserved"),
            "description": _("Crop without any quality loss - content stays sharp"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Apply to Multiple Pages"),
            "description": _("Crop all pages, current page, or specific pages at once"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Processing"),
            "description": _("Fast cropping with immediate download"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I crop a PDF page?"),
            "answer": _(
                "Upload your PDF, click and drag to select the area you want to keep, "
                "choose which pages to apply the crop to, and click Crop PDF."
            ),
        },
        {
            "question": _("Can I crop multiple pages at once?"),
            "answer": _(
                "Yes! You can apply the same crop to all pages, just the current page, "
                "or specify pages like '1,3,5' or '1-5'."
            ),
        },
        {
            "question": _("Will cropping reduce PDF quality?"),
            "answer": _(
                "No, cropping only removes the area outside the selection. "
                "The content inside remains at its original quality."
            ),
        },
        {
            "question": _("How do I remove margins from a PDF?"),
            "answer": _(
                "Upload your PDF and draw a selection box that excludes the margins. "
                "The areas outside your selection will be removed."
            ),
        },
        {
            "question": _("Can I undo a crop after saving?"),
            "answer": _(
                "No, cropping permanently removes the areas outside the selection. "
                "Always keep a backup of your original PDF before cropping. "
                "You can preview the result before downloading."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use the corner handles to precisely resize the crop area"),
        _("Drag the selection box to reposition it"),
        _("Apply crop to all pages for consistent margins"),
        _("Use 'Scale to page size' to fill the entire page with cropped content"),
        _("Preview the cropped result before downloading to ensure it's correct"),
    ]

    # SEO Content
    context["page_content_title"] = _("Crop PDF Pages - Remove Margins Online")
    context["page_content_body"] = _(
        "<p>Our free PDF cropping tool lets you remove unwanted margins, borders, "
        "or content from your PDF pages. The visual editor makes it easy to select "
        "exactly what you want to keep.</p>"
        "<p>Perfect for trimming scanned documents, removing white borders, "
        "or focusing on specific content areas in your PDFs.</p>"
        "<p><strong>Common uses:</strong> Remove scanner margins from scanned documents, "
        "trim white space from exported slides, crop to focus on specific charts or images, "
        "or prepare PDFs for printing with custom page sizes.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("crop_pdf")
    return render(request, "frontend/pdf_edit/crop_pdf.html", context)


def merge_pdf_page(request):
    """Merge PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Merge PDF Files Online Free - Combine PDFs | Convertica"),
        page_description=_(
            "Merge PDF online free. Combine multiple PDF files into one document. "
            "Drag and drop to reorder, no watermark, no registration. "
            "Fast & secure PDF merger for all devices."
        ),
        page_keywords=(
            # Primary keywords
            "merge PDF, combine PDF, merge pdf online free, join pdf files, "
            "combine two pdfs into one, merge pdf without watermark, pdf merger, "
            # Feature-based keywords
            "merge pdf drag and drop, merge pdf reorder pages, merge pdf preserve bookmarks, "
            "merge pdf no quality loss, merge pdf keep links, combine pdf pages in order, "
            # Use case keywords
            "merge pdf thesis chapters, merge pdf invoices, merge pdf contracts, "
            "merge pdf scanned pages, merge pdf receipts, combine pdf statements, "
            "merge pdf lecture notes, merge pdf business documents, merge pdf reports, "
            # Quantity keywords
            "merge 2 pdf files, merge 3 pdfs, merge multiple pdf files, merge 10 pdfs, "
            "combine several pdfs, batch merge pdf, merge many pdfs at once, "
            # Platform keywords
            "merge pdf online, merge pdf mac, merge pdf windows, merge pdf mobile, "
            "merge pdf iphone, merge pdf android, merge pdf chromebook, "
            # Free/No registration keywords
            "merge pdf free, merge pdf no registration, merge pdf no sign up, "
            "pdf merger unlimited, merge pdf safe, merge pdf secure, "
            # Comparison keywords
            "smallpdf merge alternative, ilovepdf merge alternative, pdf merge best 2026"
        ),
        page_subtitle=_("Combine multiple PDF files into one document"),
        header_text=_("Merge PDF"),
        file_input_name="pdf_files",
        file_accept=".pdf",
        api_url_name="merge_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Merge PDFs"),
        select_file_message=_("Please select PDF files to merge."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Drag & Drop Reorder"),
            "description": _(
                "Easily arrange PDF files in any order by dragging and dropping"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("No Quality Loss"),
            "description": _(
                "Original PDF quality preserved. No compression, no watermarks added"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Secure Processing"),
            "description": _(
                "Files are encrypted during processing and deleted immediately after"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>',
            "gradient": "from-amber-500 to-orange-600",
            "title": _("Merge Up to 10 Files"),
            "description": _(
                "Combine 2-10 PDF files at once. Premium users can merge even more"
            ),
        },
    ]
    context["benefits_title"] = _("Why Merge PDFs with Convertica?")

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How many PDF files can I merge at once?"),
            "answer": _(
                "Free users can merge 2-10 PDF files in one operation. Simply select all your files, "
                "arrange them in the desired order using drag and drop, and click Merge. "
                "Premium users can merge even more files with higher page limits."
            ),
        },
        {
            "question": _("Will bookmarks and links be preserved?"),
            "answer": _(
                "Yes, internal bookmarks and hyperlinks within each PDF are preserved after merging. "
                "The merged PDF will contain all bookmarks from all source files, making navigation easy."
            ),
        },
        {
            "question": _("Can I change the order of PDF files before merging?"),
            "answer": _(
                "Yes! After selecting your files, you can drag and drop them to arrange in any order. "
                "Preview thumbnails help you see which file is which. The final merged PDF will follow "
                "the order you set."
            ),
        },
        {
            "question": _("Is there a file size limit for merging?"),
            "answer": _(
                "Free users can merge PDFs with a combined total of up to 50 pages. "
                "For larger documents, Premium subscription provides higher limits. "
                "There's no limit on individual file sizes."
            ),
        },
        {
            "question": _("Can I merge scanned PDFs?"),
            "answer": _(
                "Yes, you can merge both digital and scanned PDFs. The tool combines them "
                "as-is without any conversion. All pages from all files will be included "
                "in the merged document."
            ),
        },
    ]
    context["faq_title"] = _("Merge PDF - Frequently Asked Questions")

    # SEO Tips
    context["page_tips"] = [
        _(
            "Arrange files in the correct order before merging - use drag and drop to reorder"
        ),
        _("For large projects, merge related chapters or sections separately first"),
        _("Check page orientation - rotate pages if needed before or after merging"),
        _("Remove unnecessary pages before merging to keep file size small"),
        _(
            "After merging, you can use our Split tool to extract specific pages if needed"
        ),
    ]
    context["tips_title"] = _("Tips for Merging PDF Files")

    # SEO Content
    context["page_content_title"] = _("Merge PDF Files Online - Easy & Free")
    context["page_content_body"] = _(
        "<p>Need to combine multiple PDF documents into a single file? Our <strong>free PDF merger</strong> "
        "lets you join 2-10 PDF files quickly and easily. Perfect for combining "
        "<strong>invoices, contracts, reports, or scanned documents</strong>.</p>"
        "<p>Simply select your files, arrange them in the desired order using drag and drop, "
        "and click Merge. Your combined PDF will be ready for download in seconds. "
        "All <strong>bookmarks, hyperlinks, and formatting</strong> are preserved.</p>"
        "<p><strong>Use cases:</strong> Combine thesis chapters, merge scanned receipts, "
        "join contract pages, create document packages for clients, or organize lecture notes "
        "into a single file.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("merge_pdf")
    return render(request, "frontend/pdf_organize/merge_pdf.html", context)


def split_pdf_page(request):
    """Split PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Split PDF Online Free - Extract Pages from PDF | Convertica"),
        page_description=_(
            "Split PDF online free. Extract specific pages, split by ranges, "
            "or separate every page. No watermark, no registration. "
            "Fast PDF splitter for all devices."
        ),
        page_keywords=(
            # Primary keywords
            "split PDF, divide PDF, split pdf online free, pdf splitter, "
            "separate pdf into pages, extract pages from pdf, "
            # Feature keywords
            "split pdf by pages, split pdf by range, split pdf every page, "
            "split pdf into multiple files, pdf splitter no watermark, "
            "extract specific pages pdf, split pdf without quality loss, "
            # Use case keywords
            "extract pdf chapters, split thesis pdf, extract invoice pages, "
            "split pdf for printing, extract odd pages pdf, extract even pages, "
            "remove front page pdf, extract pdf cover page, split scanned pdf, "
            # Platform keywords
            "pdf splitter online, split pdf mac, split pdf windows, split pdf mobile, "
            "pdf splitter iphone, pdf splitter android, "
            # Free keywords
            "split pdf free, pdf splitter no registration, split pdf no ads, "
            "pdf splitter unlimited, split pdf safe, split pdf secure"
        ),
        page_subtitle=_("Split your PDF into multiple files"),
        header_text=_("Split PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="split_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".zip",
        button_text=_("Split PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Multiple Split Options"),
            "description": _(
                "Split by page ranges, extract every page, or select specific pages"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("No Quality Loss"),
            "description": _(
                "Original PDF quality preserved. Pages extracted exactly as they are"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Download as ZIP"),
            "description": _(
                "All split pages downloaded as a single ZIP file for convenience"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-amber-500 to-orange-600",
            "title": _("Secure & Private"),
            "description": _(
                "Files deleted immediately after processing. Your documents stay private"
            ),
        },
    ]
    context["benefits_title"] = _("Why Split PDFs with Convertica?")

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I split a PDF by page ranges?"),
            "answer": _(
                "Enter the page ranges you want to extract, such as '1-5, 8, 10-15'. "
                "Each range will be saved as a separate PDF file. You can also extract "
                "every page individually by selecting 'Split every page'."
            ),
        },
        {
            "question": _("Can I extract specific pages from a PDF?"),
            "answer": _(
                "Yes! Enter the page numbers you want, separated by commas (e.g., '1, 3, 5, 7'). "
                "Each specified page will be extracted to a new PDF file. "
                "You can combine individual pages and ranges."
            ),
        },
        {
            "question": _("Will splitting affect the quality of my PDF?"),
            "answer": _(
                "No, splitting preserves the original quality. Pages are extracted exactly as they are "
                "in the original document, with no re-compression or quality loss. "
                "All text, images, and formatting remain intact."
            ),
        },
        {
            "question": _("How do I download the split pages?"),
            "answer": _(
                "After splitting, all extracted pages are packaged into a ZIP file for easy download. "
                "The ZIP contains individual PDF files named with the page numbers or ranges you specified."
            ),
        },
        {
            "question": _("Is there a limit on how many pages I can split?"),
            "answer": _(
                "Free users can split PDFs up to 50 pages. Premium users have higher limits. "
                "For very large documents, you may need to process them in batches."
            ),
        },
    ]
    context["faq_title"] = _("Split PDF - Frequently Asked Questions")

    # SEO Tips
    context["page_tips"] = [
        _("Use ranges like '1-5, 10-15' to extract multiple sections at once"),
        _("Select 'Split every page' to create individual PDFs from each page"),
        _("Extract odd or even pages only for double-sided printing preparation"),
        _("For large PDFs, split into smaller parts for easier sharing via email"),
        _("After splitting, use Merge PDF to combine pages in a new order"),
    ]
    context["tips_title"] = _("Tips for Splitting PDF Files")

    # SEO Content
    context["page_content_title"] = _("Split PDF Online - Extract Pages Easily")
    context["page_content_body"] = _(
        "<p>Need to extract specific pages from a PDF? Our <strong>free PDF splitter</strong> "
        "lets you divide PDF documents by page ranges, extract individual pages, "
        "or split every page into separate files.</p>"
        "<p>Perfect for <strong>extracting chapters from ebooks, separating invoices, "
        "splitting contracts, or preparing documents for printing</strong>. "
        "The original quality is preserved - no compression or quality loss.</p>"
        "<p><strong>Flexible options:</strong> Enter page ranges (1-5, 10-15), "
        "individual pages (1, 3, 7), or split every page. All extracted pages "
        "download as a convenient ZIP file.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("split_pdf")
    return render(request, "frontend/pdf_organize/split_pdf.html", context)


def remove_pages_page(request):
    """Remove pages from PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Remove Pages from PDF Online Free | Convertica"),
        page_description=_(
            "Remove pages from PDF online free. "
            "Delete unwanted pages quickly and easily with no watermark. "
            "Fast PDF page removal tool. Perfect for cleaning up documents. "
            "No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "remove PDF pages, delete PDF pages, remove pages from pdf online free, "
            "pdf page remover, delete pages from pdf, pdf page deletion tool, "
            # Feature keywords
            "remove pdf pages no watermark, delete pdf pages fast, "
            "remove pdf pages without losing quality, remove multiple pages pdf, "
            "delete specific pages pdf, remove first page pdf, remove last page pdf, "
            # Use case keywords
            "remove blank pages pdf, delete cover page pdf, remove unwanted pages pdf, "
            "clean up pdf, remove advertisements pdf, delete empty pages pdf, "
            "remove intro pages pdf, delete appendix pdf, trim pdf pages, "
            # Quality keywords
            "remove pages pdf keep quality, delete pages pdf no compression, "
            # Platform keywords
            "pdf page removal mac, pdf page removal windows, remove pdf pages online, "
            "delete pdf pages mobile, remove pdf pages iphone, remove pdf pages android, "
            # Free keywords
            "remove pdf pages free, remove pdf pages no registration, remove pdf pages no signup, "
            "delete pdf pages free online, pdf page remover unlimited, "
            # Comparison keywords
            "smallpdf delete pages alternative, ilovepdf remove pages alternative"
        ),
        page_subtitle=_("Remove unwanted pages from your PDF"),
        header_text=_("Remove Pages"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="remove_pages_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Remove Pages"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>',
            "gradient": "from-red-500 to-red-600",
            "title": _("Quick Page Deletion"),
            "description": _("Remove unwanted pages from your PDF in seconds"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Quality Preserved"),
            "description": _("Original content quality remains unchanged"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Visual Preview"),
            "description": _("See page thumbnails before removing"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Processing"),
            "description": _("Fast removal with immediate download"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I remove pages from a PDF?"),
            "answer": _(
                "Upload your PDF, select the pages you want to remove, and click Remove Pages."
            ),
        },
        {
            "question": _("Can I remove multiple pages at once?"),
            "answer": _(
                "Yes! Select multiple pages by clicking on them or using ranges like '1,3,5' or '1-5'."
            ),
        },
        {
            "question": _("Will removing pages affect the document quality?"),
            "answer": _(
                "No, removing pages only deletes the selected pages. Remaining content stays unchanged."
            ),
        },
        {
            "question": _("Can I undo page removal after saving?"),
            "answer": _(
                "No, page removal is permanent once you download the new PDF. "
                "Always keep a backup of your original file before removing pages."
            ),
        },
        {
            "question": _("How do I remove blank pages from a PDF?"),
            "answer": _(
                "Upload your PDF, view the page thumbnails to identify blank pages, "
                "select them by clicking or using page numbers, then click Remove Pages. "
                "This is perfect for cleaning up scanned documents."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Preview pages before removing to avoid mistakes"),
        _("Use page ranges for faster selection (e.g., '1-3, 7, 10-12')"),
        _("Remove blank pages to reduce file size"),
        _("Keep a backup of your original PDF before removing pages"),
        _(
            "Use Extract Pages instead if you want to keep specific pages as a new document"
        ),
    ]

    # SEO Content
    context["page_content_title"] = _("Remove Pages from PDF - Delete Unwanted Pages")
    context["page_content_body"] = _(
        "<p>Our free PDF page remover lets you delete unwanted pages from any PDF document. "
        "Perfect for removing blank pages, cover pages, or unnecessary content.</p>"
        "<p>Simply upload your PDF, preview the pages using thumbnails, select the ones you want "
        "to remove, and download the cleaned-up document. The remaining pages maintain their "
        "original quality and formatting.</p>"
        "<p><strong>Common uses:</strong> Remove blank pages from scanned documents, delete cover pages "
        "or advertisements, trim unnecessary appendices, or clean up exported presentations before sharing.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("remove_pages")
    return render(request, "frontend/pdf_organize/remove_pages.html", context)


def extract_pages_page(request):
    """Extract pages from PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Extract Pages from PDF Online Free | Convertica"),
        page_description=_(
            "Extract pages from PDF online free. "
            "Select and extract specific pages to create a new PDF. "
            "Fast PDF page extraction tool with no watermark. "
            "Perfect for creating custom documents. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "extract PDF pages, PDF page extractor, extract pages from pdf online free, "
            "select pdf pages, pdf page extraction tool, get specific pages from pdf, "
            # Feature keywords
            "extract pdf pages no watermark, extract specific pages pdf, "
            "extract pdf pages by range, extract pdf pages by number, "
            "extract single page from pdf, extract multiple pages pdf, "
            # Use case keywords
            "extract chapter from pdf, extract cover page pdf, extract table of contents pdf, "
            "extract odd pages pdf, extract even pages pdf, extract first page pdf, "
            "extract last page pdf, extract middle pages pdf, extract specific section pdf, "
            # Quality keywords
            "extract pdf pages keep quality, extract pages pdf no compression, "
            # Platform keywords
            "extract pdf pages mac, extract pdf pages windows, extract pdf pages online, "
            "extract pdf pages mobile, extract pdf pages iphone, extract pdf pages android, "
            # Free keywords
            "extract pdf pages free, extract pdf pages no registration, extract pdf pages no signup, "
            "pdf page extractor unlimited, extract pages pdf safe, "
            # Comparison keywords
            "smallpdf extract pages alternative, ilovepdf extract alternative"
        ),
        page_subtitle=_("Extract specific pages from your PDF"),
        header_text=_("Extract Pages"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="extract_pages_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Extract Pages"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Flexible Selection"),
            "description": _(
                "Extract individual pages, ranges, or specific combinations"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Quality Preserved"),
            "description": _("Extracted pages maintain original quality"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("New PDF Created"),
            "description": _("Get a new PDF containing only your selected pages"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Processing"),
            "description": _("Fast extraction with immediate download"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I extract specific pages from a PDF?"),
            "answer": _(
                "Upload your PDF, select the pages you want (e.g., '1,3,5' or '1-10'), and click Extract."
            ),
        },
        {
            "question": _("What's the difference between Extract and Split?"),
            "answer": _(
                "Extract creates one new PDF with selected pages. Split creates multiple separate PDFs."
            ),
        },
        {
            "question": _("Can I extract non-consecutive pages?"),
            "answer": _(
                "Yes! Use comma-separated page numbers like '1,3,7,15' to extract specific pages."
            ),
        },
        {
            "question": _("Will extracted pages maintain their original quality?"),
            "answer": _(
                "Yes, extracted pages are identical to the originals. No compression or quality loss occurs. "
                "All text, images, and formatting remain exactly as in the source PDF."
            ),
        },
        {
            "question": _("Can I extract pages from a password-protected PDF?"),
            "answer": _(
                "You'll need to unlock the PDF first using our Unlock PDF tool. "
                "Once unlocked, you can extract any pages you need."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use ranges for consecutive pages (e.g., '1-10')"),
        _("Combine ranges and individual pages (e.g., '1-5,8,10-15')"),
        _("Preview pages before extracting to ensure correct selection"),
        _("Extract odd or even pages for double-sided printing needs"),
        _("Use Extract instead of Split when you need just one combined PDF"),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "Extract Pages from PDF - Create Custom Documents"
    )
    context["page_content_body"] = _(
        "<p>Our free PDF page extractor lets you select and extract specific pages to create "
        "a new PDF document. Perfect for extracting chapters, important sections, or creating "
        "custom document packages.</p>"
        "<p>Select individual pages, ranges like '1-10', or combinations like '1-5, 8, 12-15'. "
        "The extracted pages are combined into a new PDF that you can download immediately. "
        "All formatting and quality are preserved.</p>"
        "<p><strong>Common uses:</strong> Extract specific chapters from ebooks, pull out important "
        "contract sections, create document excerpts for sharing, extract forms from multi-page documents, "
        "or prepare specific pages for printing.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("extract_pages")
    return render(request, "frontend/pdf_organize/extract_pages.html", context)


def organize_pdf_page(request):
    """Organize PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Organize PDF Online Free - Reorder Pages | Convertica"),
        page_description=_(
            "Organize PDF online free. "
            "Reorder pages, sort content, and manage your PDF files "
            "with drag and drop. Fast PDF organizer with no watermark. "
            "Perfect for organizing documents and reports. No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "organize PDF, PDF organizer, organize pdf online free, "
            "reorder pdf pages, pdf page organizer, rearrange pdf pages, "
            # Feature keywords
            "reorder pdf pages drag and drop, sort pdf pages, change pdf page order, "
            "move pdf pages, swap pdf pages, pdf page sorting tool, "
            # Use case keywords
            "organize pdf for presentation, fix pdf page order, reorder scanned pdf, "
            "sort pdf documents, fix scanned document order, organize report pages, "
            "arrange pdf slides, reorder contract pages, organize thesis chapters, "
            # Quality keywords
            "reorder pdf pages no quality loss, organize pdf keep formatting, "
            # Platform keywords
            "organize pdf mac, organize pdf windows, reorder pdf online, "
            "pdf organizer mobile, reorder pdf iphone, reorder pdf android, "
            # Free keywords
            "organize pdf free, organize pdf no registration, reorder pdf no signup, "
            "pdf organizer unlimited, organize pdf no watermark, "
            # Comparison keywords
            "smallpdf organize alternative, ilovepdf reorder alternative"
        ),
        page_subtitle=_("Organize and manage your PDF documents"),
        header_text=_("Organize PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="organize_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Organize PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Drag & Drop Reorder"),
            "description": _("Easily rearrange pages by dragging and dropping"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Page Thumbnails"),
            "description": _("See visual previews of all pages for easy organization"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Quality Preserved"),
            "description": _("Page order changes without affecting content quality"),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Processing"),
            "description": _("Save your new page order with one click"),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I reorder pages in a PDF?"),
            "answer": _(
                "Upload your PDF, drag and drop page thumbnails to rearrange them, then click Save."
            ),
        },
        {
            "question": _("Can I also delete pages while organizing?"),
            "answer": _(
                "Use our dedicated Remove Pages tool to delete pages. Organize is for reordering only."
            ),
        },
        {
            "question": _("Will reordering affect the document quality?"),
            "answer": _(
                "No, reordering only changes page sequence. All content remains unchanged."
            ),
        },
        {
            "question": _("Can I move multiple pages at once?"),
            "answer": _(
                "Yes, you can select multiple pages and drag them together to a new position. "
                "This makes it easy to move entire sections of your document."
            ),
        },
        {
            "question": _("Is there a limit on the number of pages I can organize?"),
            "answer": _(
                "Free users can organize PDFs with up to 50 pages. "
                "For larger documents, Premium subscription provides higher limits."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _("Use page thumbnails to identify pages quickly"),
        _("Drag multiple pages at once for bulk reordering"),
        _("Review the final order before saving"),
        _("Combine with Merge PDF to organize pages from multiple documents"),
        _("Use Rotate PDF first if some pages are upside down"),
    ]

    # SEO Content
    context["page_content_title"] = _("Organize PDF Pages - Reorder and Rearrange")
    context["page_content_body"] = _(
        "<p>Our free PDF organizer lets you reorder pages in any PDF document using simple "
        "drag and drop. Perfect for fixing page order, organizing scanned documents, "
        "or preparing presentations.</p>"
        "<p>Simply upload your PDF, view page thumbnails, and drag pages to rearrange them. "
        "The visual interface makes it easy to see exactly how your document will look. "
        "All content and formatting remain unchanged.</p>"
        "<p><strong>Common uses:</strong> Fix incorrectly ordered scanned documents, "
        "rearrange presentation slides, organize report sections, reorder contract pages, "
        "or prepare documents for printing in the correct sequence.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("organize_pdf")
    return render(request, "frontend/pdf_organize/organize_pdf.html", context)


def pdf_to_excel_page(request):
    """PDF to Excel conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to Excel - Convertica"),
        page_description=_(
            "Convert PDF to Excel online free with accurate table extraction. "
            "Extract tables from PDF and convert to XLSX format. "
            "Perfect for invoices, reports, and data analysis. "
            "No registration required."
        ),
        page_keywords=(
            "PDF to Excel, PDF to XLSX, convert PDF to Excel online free, "
            "pdf to excel without losing formatting, extract tables from pdf to excel, "
            "pdf table to excel converter, pdf to excel converter no email, "
            "pdf to excel fast online, convert pdf spreadsheet to excel, "
            "pdf to xlsx converter online free, pdf to excel converter unlimited, "
            "pdf to excel converter no sign up, convert pdf data to excel, "
            "pdf to excel export free, pdf to excel maintain formatting, "
            "pdf to excel high accuracy, convert pdf invoice to excel, "
            "pdf to excel batch converter, convert multiple pdf to excel online, "
            "pdf to excel no ads, pdf to excel no virus, "
            "pdf to excel converter small file, pdf to excel converter large file, "
            "pdf to excel converter clean layout, pdf to excel converter best 2025, "
            "pdf to excel converter high accuracy, pdf to excel converter for mac online, "
            "pdf to excel for linux online, pdf to excel converter for students, "
            "free pdf to excel tool safe, pdf to excel without registration, "
            "pdf to excel one click, extract pdf table to excel, "
            "pdf to excel keep formatting, pdf to excel high resolution, "
            "pdf to excel for invoices, pdf to excel for reports, "
            "pdf to excel google drive safe, pdf to excel cloud converter, "
            "pdf to excel export data only, pdf data to excel converter, "
            "pdf to excel editor included, pdf to excel converter without errors, "
            "convert pdf spreadsheet to excel, convert pdf data table to excel, "
            "pdf to excel table alignment maintained, pdf to excel for accounting, "
            "pdf to excel for business"
        ),
        page_subtitle=_("Extract tables from PDF and convert to Excel format"),
        header_text=_("PDF to Excel Converter"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_excel_api",
        replace_regex=r"\.pdf$",
        replace_to=".xlsx",
        button_text=_("Convert PDF to Excel"),
        select_file_message=_("Please select a PDF file with tables."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Accurate Table Extraction"),
            "description": _(
                "Our advanced AI-powered engine accurately extracts tables from PDF "
                "documents and converts them to editable Excel spreadsheets with "
                "preserved cell structure and formatting."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Lightning Fast Conversion"),
            "description": _(
                "Convert PDF to Excel in seconds. Our optimized servers process "
                "your documents quickly so you can start working with your data immediately."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Secure Data Handling"),
            "description": _(
                "Your PDF files are processed securely and automatically deleted "
                "after conversion. We never store or share your sensitive financial data."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("100% Free Service"),
            "description": _(
                "Convert PDF to Excel completely free without watermarks, email "
                "registration, or hidden fees. Perfect for invoices, reports, and financial data."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a PDF with tables to Excel?"),
            "answer": _(
                "Simply upload your PDF file using the button above, then click "
                "'Convert PDF to Excel'. Our system will automatically detect and extract "
                "all tables from your PDF and convert them to an editable Excel spreadsheet (XLSX format)."
            ),
        },
        {
            "question": _("Will the table formatting be preserved after conversion?"),
            "answer": _(
                "Yes, our PDF to Excel converter preserves cell structure, borders, and data alignment. "
                "Merged cells, column widths, and row heights are maintained to give you "
                "an accurate Excel representation of your PDF tables."
            ),
        },
        {
            "question": _("Can I convert scanned PDF documents to Excel?"),
            "answer": _(
                "Our converter works best with text-based PDF documents. For scanned PDFs, "
                "the quality of extraction depends on the scan quality. For best results, "
                "use PDFs that were created digitally or have clear, high-resolution scans."
            ),
        },
        {
            "question": _("Is there a limit on the number of PDF pages I can convert?"),
            "answer": _(
                "Free users can convert PDF files with a reasonable page limit. For larger "
                "documents with many tables, consider splitting your PDF into smaller sections "
                "for optimal conversion quality."
            ),
        },
        {
            "question": _("What types of PDFs work best for Excel conversion?"),
            "answer": _(
                "PDFs containing structured data like invoices, financial reports, bank statements, "
                "price lists, inventory sheets, and data tables convert most accurately. "
                "Documents with complex layouts or images may require manual adjustments."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "For best results, use PDFs with clearly defined table borders and consistent formatting."
        ),
        _(
            "If your PDF has multiple tables, they will each be placed on separate sheets in Excel."
        ),
        _(
            "Check the converted Excel file for any cells that may need manual adjustment after conversion."
        ),
        _(
            "Use PDFs created from spreadsheet applications for the most accurate conversion results."
        ),
        _(
            "For large PDFs with many pages, consider splitting them before conversion for faster processing."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _("Professional PDF to Excel Conversion")
    context["page_content_body"] = _(
        "<p>Converting PDF documents to Excel spreadsheets is essential for modern business "
        "workflows. Whether you're extracting financial data from invoices, analyzing reports, "
        "or importing data from PDF tables into your accounting software, our PDF to Excel "
        "converter makes the process simple and accurate.</p>"
        "<p>Our advanced conversion technology uses intelligent table detection to identify "
        "rows, columns, and cell boundaries in your PDF documents. The extracted data is then "
        "formatted as a proper Excel spreadsheet, ready for editing, calculations, and analysis. "
        "This eliminates hours of manual data entry and reduces the risk of transcription errors.</p>"
        "<p>Perfect for accountants, financial analysts, data entry professionals, and anyone "
        "who needs to work with data locked in PDF format. Convert bank statements, invoices, "
        "purchase orders, inventory lists, and any other tabular PDF documents to editable "
        "Excel files in just a few clicks.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("pdf_to_excel")
    return render(request, "frontend/pdf_convert/pdf_to_excel.html", context)


def excel_to_pdf_page(request):
    """Excel to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("Excel to PDF - Convertica"),
        page_description=_(
            "Convert Excel to PDF online free with high quality. "
            "Convert XLS and XLSX spreadsheets to PDF format. "
            "Preserve formatting, charts, and formulas. "
            "No registration required."
        ),
        page_keywords=(
            "Excel to PDF, XLSX to PDF, XLS to PDF, convert Excel to PDF online free, "
            "excel to pdf without losing formatting, excel spreadsheet to pdf, "
            "xlsx to pdf converter no email, excel to pdf fast online, "
            "convert excel workbook to pdf, xlsx to pdf online free, "
            "excel to pdf converter unlimited, excel to pdf converter no sign up, "
            "convert excel data to pdf, excel to pdf export free, "
            "excel to pdf maintain formatting, excel to pdf high quality, "
            "convert excel invoice to pdf, excel to pdf batch converter, "
            "convert multiple excel to pdf online, excel to pdf no ads, "
            "excel to pdf converter best 2025, excel to pdf for business"
        ),
        page_subtitle=_("Convert Excel spreadsheets to PDF format"),
        header_text=_("Excel to PDF Converter"),
        file_input_name="excel_file",
        file_accept=".xls,.xlsx",
        api_url_name="excel_to_pdf_api",
        replace_regex=r"\.(xlsx?|XLSX?)$",
        replace_to=".pdf",
        button_text=_("Convert to PDF"),
        select_file_message=_("Please select an Excel file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Perfect Formatting Preservation"),
            "description": _(
                "Convert Excel spreadsheets to PDF while maintaining all formatting, "
                "including fonts, colors, borders, merged cells, and column widths. "
                "Your PDF will look exactly like your Excel file."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Charts & Graphics Support"),
            "description": _(
                "All charts, graphs, images, and graphics in your Excel file are "
                "accurately converted to PDF. Perfect for financial reports and presentations."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Multi-Sheet Conversion"),
            "description": _(
                "Excel workbooks with multiple sheets are converted seamlessly. "
                "Each worksheet becomes a separate section in your PDF document."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Secure & Private"),
            "description": _(
                "Your Excel files are processed securely and deleted immediately after conversion. "
                "No data is stored on our servers. Perfect for confidential business documents."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert Excel to PDF online?"),
            "answer": _(
                "Simply upload your Excel file (XLS or XLSX) using the button above, "
                "then click 'Convert to PDF'. Your spreadsheet will be converted to a "
                "high-quality PDF file that you can download immediately."
            ),
        },
        {
            "question": _("Will my Excel formatting be preserved in the PDF?"),
            "answer": _(
                "Yes, our converter preserves all formatting including fonts, colors, borders, "
                "cell alignment, merged cells, and column widths. Charts, images, and graphics "
                "are also accurately converted."
            ),
        },
        {
            "question": _("Can I convert Excel files with multiple sheets?"),
            "answer": _(
                "Yes, Excel workbooks with multiple worksheets are fully supported. "
                "Each sheet will be converted and included in the final PDF document "
                "as separate pages or sections."
            ),
        },
        {
            "question": _("What Excel formats are supported?"),
            "answer": _(
                "We support both XLS (Excel 97-2003) and XLSX (Excel 2007 and later) formats. "
                "Simply upload your file and it will be converted to PDF automatically."
            ),
        },
        {
            "question": _("Is there a file size limit for Excel to PDF conversion?"),
            "answer": _(
                "Free users can convert Excel files within reasonable size limits. "
                "For very large spreadsheets with many rows or complex formulas, "
                "consider splitting them into smaller files for optimal results."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "Set your print area in Excel before converting to control which cells appear in the PDF."
        ),
        _(
            "Adjust page orientation (portrait/landscape) in Excel for better PDF output."
        ),
        _(
            "Use 'Fit to Page' settings in Excel to ensure all columns fit on one page width."
        ),
        _("Remove hidden rows and columns before conversion to reduce PDF file size."),
        _(
            "Check print preview in Excel to see how your PDF will look before converting."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _("Convert Excel Spreadsheets to Professional PDFs")
    context["page_content_body"] = _(
        "<p>Converting Excel spreadsheets to PDF format is essential for sharing financial reports, "
        "invoices, and business documents. PDF ensures your carefully formatted spreadsheets "
        "look identical on any device, without requiring recipients to have Excel installed.</p>"
        "<p>Our Excel to PDF converter handles complex spreadsheets with ease, preserving all "
        "formatting elements including conditional formatting, data bars, charts, and images. "
        "Whether you're converting a simple data table or a complex financial model with "
        "multiple worksheets, the output PDF maintains professional quality.</p>"
        "<p>Perfect for accountants sharing reports with clients, businesses sending invoices, "
        "analysts distributing data summaries, and anyone who needs to convert Excel files "
        "to a universal, non-editable format for secure distribution.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("excel_to_pdf")
    return render(request, "frontend/pdf_convert/excel_to_pdf.html", context)


def ppt_to_pdf_page(request):
    """PowerPoint to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PowerPoint to PDF - Convertica"),
        page_description=_(
            "Convert PowerPoint to PDF online free with high quality. "
            "Convert PPT and PPTX presentations to PDF format. "
            "Preserve slides, animations, and formatting. "
            "No registration required."
        ),
        page_keywords=(
            "PowerPoint to PDF, PPT to PDF, PPTX to PDF, convert PowerPoint to PDF online free, "
            "ppt to pdf without losing formatting, powerpoint presentation to pdf, "
            "pptx to pdf converter no email, ppt to pdf fast online, "
            "convert powerpoint slides to pdf, pptx to pdf online free, "
            "ppt to pdf converter unlimited, ppt to pdf converter no sign up, "
            "convert presentation to pdf, ppt to pdf export free, "
            "ppt to pdf maintain formatting, ppt to pdf high quality, "
            "convert ppt slides to pdf, ppt to pdf batch converter, "
            "ppt to pdf no ads, ppt to pdf converter best 2025"
        ),
        page_subtitle=_("Convert PowerPoint presentations to PDF format"),
        header_text=_("PowerPoint to PDF Converter"),
        file_input_name="ppt_file",
        file_accept=".ppt,.pptx",
        api_url_name="ppt_to_pdf_api",
        replace_regex=r"\.(pptx?|PPTX?)$",
        replace_to=".pdf",
        button_text=_("Convert to PDF"),
        select_file_message=_("Please select a PowerPoint file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
            "gradient": "from-orange-500 to-red-500",
            "title": _("Slide-Perfect Conversion"),
            "description": _(
                "Every slide in your PowerPoint is converted to PDF with pixel-perfect accuracy. "
                "Fonts, colors, transitions, and layouts are preserved exactly as designed."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Images & Graphics Preserved"),
            "description": _(
                "All images, charts, SmartArt, and graphics in your presentation are "
                "converted with high quality. Perfect for sharing visual presentations."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Speaker Notes Optional"),
            "description": _(
                "Convert slides with or without speaker notes. Share clean presentations "
                "with clients or include notes for detailed documentation."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Instant Conversion"),
            "description": _(
                "Convert PowerPoint presentations to PDF in seconds. No software installation "
                "required - works directly in your browser on any device."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert PowerPoint to PDF online?"),
            "answer": _(
                "Upload your PPT or PPTX file using the button above, then click 'Convert to PDF'. "
                "Your presentation will be converted to a high-quality PDF file that preserves "
                "all slides, images, and formatting."
            ),
        },
        {
            "question": _("Will animations and transitions be preserved?"),
            "answer": _(
                "PDF format doesn't support animations or transitions. Each slide will be "
                "converted as a static page in the PDF. For animated content, consider "
                "exporting as a video format instead."
            ),
        },
        {
            "question": _("Can I convert presentations with embedded videos?"),
            "answer": _(
                "Embedded videos cannot be included in PDF files. Video frames will appear "
                "as static images in the converted PDF. Audio content is also not included "
                "in PDF output."
            ),
        },
        {
            "question": _("What PowerPoint formats are supported?"),
            "answer": _(
                "We support both PPT (PowerPoint 97-2003) and PPTX (PowerPoint 2007 and later) "
                "formats. OpenDocument presentations (ODP) can also be converted."
            ),
        },
        {
            "question": _("How can I reduce the PDF file size?"),
            "answer": _(
                "Large presentations with many high-resolution images will create larger PDFs. "
                "To reduce file size, compress images in PowerPoint before converting, or use "
                "our PDF compression tool after conversion."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "Check your slide master and templates before converting to ensure consistent formatting."
        ),
        _(
            "Use standard fonts or embed fonts in PowerPoint to avoid font substitution issues."
        ),
        _(
            "Set your desired slide size in PowerPoint before converting for optimal PDF dimensions."
        ),
        _("Remove hidden slides before conversion if you don't want them in the PDF."),
        _("Use high-quality images in your presentation for best results in the PDF."),
    ]

    # SEO Content
    context["page_content_title"] = _("Convert PowerPoint Presentations to PDF")
    context["page_content_body"] = _(
        "<p>Converting PowerPoint presentations to PDF format ensures your slides can be viewed "
        "on any device without requiring PowerPoint software. PDF preserves your design, fonts, "
        "and layouts exactly as you created them, making it the preferred format for sharing "
        "presentations with clients, colleagues, or audiences.</p>"
        "<p>Our PowerPoint to PDF converter handles complex presentations with multiple slides, "
        "embedded images, charts, and custom formatting. Whether you're converting a business "
        "proposal, educational lecture, or marketing pitch deck, the output PDF maintains "
        "professional quality and visual fidelity.</p>"
        "<p>Perfect for businesses sharing proposals, educators distributing course materials, "
        "students submitting assignments, and anyone who needs to convert presentations to "
        "a universal format for easy viewing and printing.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("ppt_to_pdf")
    return render(request, "frontend/pdf_convert/ppt_to_pdf.html", context)


def html_to_pdf_page(request):
    """HTML to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("HTML to PDF - Convertica"),
        page_description=_(
            "Convert HTML to PDF online free with high quality. "
            "Convert HTML content and web pages to PDF format. "
            "Preserve styling, images, and layout. "
            "No registration required."
        ),
        page_keywords=(
            "HTML to PDF, web page to PDF, URL to PDF, convert HTML to PDF online free, "
            "html to pdf without losing formatting, html content to pdf, "
            "url to pdf converter no email, html to pdf fast online, "
            "convert web page to pdf, html to pdf online free, "
            "html to pdf converter unlimited, html to pdf converter no sign up, "
            "convert html string to pdf, html to pdf export free, "
            "html to pdf maintain styling, html to pdf high quality, "
            "save webpage as pdf, html to pdf batch converter, "
            "html to pdf no ads, html to pdf converter best 2025"
        ),
        page_subtitle=_("Convert HTML content and web pages to PDF format"),
        header_text=_("HTML to PDF Converter"),
        file_input_name="html_content",
        file_accept="",
        api_url_name="html_to_pdf_api",
        replace_regex=r"",
        replace_to=".pdf",
        button_text=_("Convert to PDF"),
        select_file_message=_("Please enter HTML content or URL."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("URL to PDF Conversion"),
            "description": _(
                "Convert any public web page to PDF by simply entering its URL. "
                "Our service captures the page exactly as it appears in a browser, "
                "including images, styles, and layout."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("HTML Code to PDF"),
            "description": _(
                "Paste your HTML code directly and convert it to PDF. Perfect for "
                "developers, designers, and anyone working with HTML content that "
                "needs to be exported as a document."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Customizable Page Settings"),
            "description": _(
                "Control page size (A4, Letter, Legal) and margins to get exactly "
                "the PDF layout you need. Perfect for printing or document archiving."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Fast & Reliable"),
            "description": _(
                "Our powerful rendering engine converts HTML and web pages to PDF "
                "quickly and accurately. CSS, JavaScript, and modern web features are supported."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a web page URL to PDF?"),
            "answer": _(
                "Select the 'URL to PDF' tab, enter the full URL of the web page "
                "(including https://), customize page settings if needed, then click "
                "'Convert URL to PDF'. The page will be captured and converted to a downloadable PDF."
            ),
        },
        {
            "question": _("Can I convert HTML code directly to PDF?"),
            "answer": _(
                "Yes! Select the 'HTML Content' tab and paste your HTML code into the text area. "
                "You can include CSS styles inline or in <style> tags. Click 'Convert to PDF' "
                "to generate your PDF document."
            ),
        },
        {
            "question": _("Will CSS styles be preserved in the PDF?"),
            "answer": _(
                "Yes, CSS styles are fully supported. Inline styles, embedded stylesheets, "
                "and external CSS (for URL conversion) are all rendered in the PDF. "
                "Modern CSS features like flexbox and grid are supported."
            ),
        },
        {
            "question": _("Can I convert password-protected web pages?"),
            "answer": _(
                "Our converter can only access publicly available web pages. Pages that require "
                "login or authentication cannot be converted. For private content, copy the HTML "
                "source and use the 'HTML Content' option instead."
            ),
        },
        {
            "question": _("What page sizes are available?"),
            "answer": _(
                "We support A4, A3, A5, Letter, and Legal page sizes. You can also customize "
                "margins (top, bottom, left, right) in centimeters to get the exact layout you need."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "For URL conversion, ensure the page is publicly accessible without login requirements."
        ),
        _(
            "When converting HTML, include all CSS styles inline or in <style> tags for best results."
        ),
        _("Use print-friendly CSS media queries in your HTML for optimal PDF output."),
        _("Adjust margins to leave space for binding if you plan to print the PDF."),
        _(
            "Test with a simple page first to understand how your content will be rendered."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _("Convert HTML and Web Pages to PDF Documents")
    context["page_content_body"] = _(
        "<p>Converting HTML content and web pages to PDF is essential for archiving, "
        "sharing, and printing web-based information. Whether you need to save an article, "
        "create documentation from a web page, or convert your HTML email templates to PDF, "
        "our converter handles it all.</p>"
        "<p>Our HTML to PDF converter uses a powerful rendering engine that accurately "
        "captures web content including complex layouts, images, fonts, and CSS styling. "
        "The result is a professional PDF document that looks exactly like the original "
        "web page, ready for distribution or printing.</p>"
        "<p>Perfect for developers creating PDF reports from HTML templates, marketers "
        "archiving web campaigns, researchers saving online articles, and anyone who needs "
        "to convert web content to a portable document format.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("html_to_pdf")
    return render(request, "frontend/pdf_convert/html_to_pdf.html", context)


def pdf_to_ppt_page(request):
    """PDF to PowerPoint conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to PowerPoint - Convertica"),
        page_description=_(
            "Convert PDF to PowerPoint online free with high quality. "
            "Extract PDF pages and convert to PPTX presentation format. "
            "Perfect for creating editable presentations from PDF documents. "
            "No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "PDF to PowerPoint, PDF to PPT, PDF to PPTX, convert PDF to PowerPoint online free, "
            "pdf to ppt converter, pdf to powerpoint converter, pdf slides to pptx, "
            # Feature keywords
            "pdf to ppt keep formatting, pdf to powerpoint editable, pdf to ppt with images, "
            "pdf to ppt maintain layout, convert pdf pages to slides, pdf to ppt high quality, "
            # Use case keywords
            "convert pdf presentation to ppt, pdf report to powerpoint, pdf ebook to slides, "
            "pdf document to presentation, convert lecture pdf to ppt, pdf to ppt for teaching, "
            "pdf to ppt for meeting, convert scanned pdf to powerpoint, "
            # Platform keywords
            "pdf to ppt mac, pdf to ppt windows, pdf to powerpoint online, "
            "pdf to ppt mobile, pdf to ppt iphone, pdf to ppt android, "
            # Free keywords
            "pdf to ppt free, pdf to powerpoint no registration, pdf to ppt no signup, "
            "pdf to pptx no watermark, pdf to powerpoint unlimited, pdf to ppt safe, "
            # Comparison keywords
            "smallpdf pdf to ppt alternative, ilovepdf to powerpoint alternative, "
            "adobe pdf to powerpoint alternative, best pdf to ppt converter 2026"
        ),
        page_subtitle=_("Convert PDF documents to PowerPoint presentations"),
        header_text=_("PDF to PowerPoint Converter"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_ppt_api",
        replace_regex=r"\.pdf$",
        replace_to=".pptx",
        button_text=_("Convert PDF to PowerPoint"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>',
            "gradient": "from-orange-500 to-red-500",
            "title": _("Page-to-Slide Conversion"),
            "description": _(
                "Each page of your PDF is converted to an individual PowerPoint slide. "
                "Perfect for repurposing PDF documents into editable presentations."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Fully Editable Output"),
            "description": _(
                "The resulting PowerPoint presentation is fully editable. Add, remove, "
                "or modify content, change layouts, and customize your slides as needed."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Images & Graphics Preserved"),
            "description": _(
                "All images, charts, and graphics from your PDF are extracted and "
                "placed on the corresponding PowerPoint slides with high quality."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Quick & Easy"),
            "description": _(
                "Convert your PDF to PowerPoint in seconds. No software installation "
                "required - works directly in your browser on any device."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a PDF to PowerPoint?"),
            "answer": _(
                "Upload your PDF file using the button above, then click 'Convert PDF to PowerPoint'. "
                "Each page of your PDF will be converted to a PowerPoint slide, preserving images "
                "and layout as closely as possible."
            ),
        },
        {
            "question": _("Will text be editable after conversion?"),
            "answer": _(
                "Text is extracted from your PDF and placed in editable text boxes on each slide. "
                "Some complex layouts may require manual adjustment after conversion. "
                "Scanned PDFs without embedded text may not have editable text."
            ),
        },
        {
            "question": _("Can I convert PDFs with complex layouts?"),
            "answer": _(
                "Our converter handles most PDF layouts well. However, very complex layouts "
                "with overlapping elements may require some manual adjustment in PowerPoint. "
                "Simple, clean PDF layouts convert most accurately."
            ),
        },
        {
            "question": _("What's the maximum PDF size I can convert?"),
            "answer": _(
                "Free users can convert PDFs within reasonable page limits. For larger documents, "
                "consider splitting your PDF into smaller sections before conversion for optimal results."
            ),
        },
        {
            "question": _("Is the original PDF modified during conversion?"),
            "answer": _(
                "No, your original PDF file is never modified. We create a new PowerPoint "
                "presentation from your PDF content. Your source file remains unchanged."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "PDFs with clear, simple layouts convert most accurately to PowerPoint slides."
        ),
        _("For scanned PDFs, ensure good image quality for better text recognition."),
        _(
            "After conversion, check each slide and adjust text boxes or images as needed."
        ),
        _(
            "Use the converted presentation as a starting point and customize with PowerPoint's tools."
        ),
        _(
            "For presentations with many slides, consider converting smaller sections separately."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "Convert PDF Documents to Editable PowerPoint Presentations"
    )
    context["page_content_body"] = _(
        "<p>Converting PDF files to PowerPoint presentations allows you to repurpose existing "
        "documents for meetings, lectures, and presentations. Our PDF to PowerPoint converter "
        "transforms each PDF page into an individual slide, making it easy to edit, annotate, "
        "and present your content.</p>"
        "<p>Whether you have a PDF report that needs to be presented at a meeting, course "
        "materials that need to be converted to slides, or any document that would work better "
        "as a presentation, our converter provides a quick and accurate solution.</p>"
        "<p>Perfect for business professionals preparing presentations, educators creating "
        "lecture materials, students working on projects, and anyone who needs to transform "
        "static PDF documents into dynamic PowerPoint presentations.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("pdf_to_ppt")
    return render(request, "frontend/pdf_convert/pdf_to_ppt.html", context)


def pdf_to_html_page(request):
    """PDF to HTML conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to HTML - Convertica"),
        page_description=_(
            "Convert PDF to HTML online free with text extraction. "
            "Extract content from PDF and convert to HTML format. "
            "Perfect for web publishing and content management. "
            "No registration required."
        ),
        page_keywords=(
            # Primary keywords
            "PDF to HTML, convert PDF to HTML online free, pdf to html converter, "
            "pdf to web page, pdf to html with images, extract text from pdf to html, "
            # Feature keywords
            "pdf to html keep formatting, pdf to html responsive, pdf to html embedded images, "
            "pdf to html clean code, pdf to html maintain layout, pdf to html searchable, "
            # Use case keywords
            "pdf to html for website, pdf to html for cms, pdf to html for wordpress, "
            "pdf to html for blog, convert ebook pdf to html, pdf to html for seo, "
            "publish pdf as webpage, pdf content to web, pdf to html for accessibility, "
            # Quality keywords
            "pdf to html high quality, pdf to html accurate, pdf to html best converter, "
            # Platform keywords
            "pdf to html mac, pdf to html windows, pdf to html online, pdf to html mobile, "
            # Free keywords
            "pdf to html free, pdf to html no registration, pdf to html no signup, "
            "pdf to html no watermark, pdf to html unlimited, "
            # Technical keywords
            "pdf to html5, pdf to responsive html, pdf to html css, pdf to semantic html"
        ),
        page_subtitle=_("Convert PDF documents to HTML format"),
        header_text=_("PDF to HTML Converter"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_html_api",
        replace_regex=r"\.pdf$",
        replace_to=".html",
        button_text=_("Convert PDF to HTML"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Clean HTML Output"),
            "description": _(
                "Convert your PDF to clean, well-structured HTML code. The output "
                "is ready for web publishing, content management systems, or further editing."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Images Embedded"),
            "description": _(
                "Images from your PDF are automatically converted and embedded as base64 "
                "data URLs, making your HTML file completely self-contained."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Text Extraction"),
            "description": _(
                "All text content is extracted from your PDF and properly formatted "
                "in HTML. Perfect for content migration and web publishing workflows."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Web-Ready Format"),
            "description": _(
                "The converted HTML is ready to be published on any website or "
                "imported into your CMS. Compatible with all modern browsers."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I convert a PDF to HTML?"),
            "answer": _(
                "Upload your PDF file using the button above, then click 'Convert PDF to HTML'. "
                "Your PDF content will be extracted and converted to HTML format, ready for "
                "download and web publishing."
            ),
        },
        {
            "question": _("Will images from my PDF be included in the HTML?"),
            "answer": _(
                "Yes, images from your PDF are automatically extracted and embedded in the HTML "
                "file as base64 data URLs. This means your HTML file is completely self-contained "
                "and doesn't require separate image files."
            ),
        },
        {
            "question": _("Can I edit the HTML after conversion?"),
            "answer": _(
                "The converted HTML is standard HTML code that can be opened and edited "
                "in any text editor or HTML editor. You can modify the content, styling, "
                "and structure as needed."
            ),
        },
        {
            "question": _("Is the HTML compatible with all browsers?"),
            "answer": _(
                "Yes, the generated HTML uses standard HTML5 markup that is compatible "
                "with all modern web browsers including Chrome, Firefox, Safari, and Edge."
            ),
        },
        {
            "question": _("Can I use the HTML on my website?"),
            "answer": _(
                "Yes, the converted HTML can be directly uploaded to your website or "
                "imported into content management systems like WordPress, Drupal, or Joomla. "
                "You may want to add your own CSS styling for better integration."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "For best results, use PDFs with clear text content rather than scanned images."
        ),
        _(
            "Add your own CSS stylesheet to the HTML for custom styling that matches your website."
        ),
        _(
            "Check the converted HTML for any formatting that may need manual adjustment."
        ),
        _(
            "Large PDFs with many images will create larger HTML files due to embedded images."
        ),
        _(
            "Consider using a code editor with HTML formatting to review and edit the output."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "Convert PDF Documents to HTML for Web Publishing"
    )
    context["page_content_body"] = _(
        "<p>Converting PDF documents to HTML format opens up new possibilities for content "
        "distribution and web publishing. HTML is the standard format for web pages, making "
        "your content accessible to anyone with a web browser.</p>"
        "<p>Our PDF to HTML converter extracts text, images, and basic formatting from your "
        "PDF and generates clean HTML code. This is perfect for migrating content to websites, "
        "creating web-accessible versions of documents, or extracting content for further editing.</p>"
        "<p>Ideal for content managers publishing documents online, developers extracting content "
        "for web applications, and anyone who needs to make PDF content available on the web "
        "in a searchable, accessible format.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("pdf_to_html")
    return render(request, "frontend/pdf_convert/pdf_to_html.html", context)


def compress_pdf_page(request):
    """Compress PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Compress PDF Online Free - Reduce PDF Size | Convertica"),
        page_description=_(
            "Compress PDF online free to reduce file size. "
            "Shrink PDF for email (under 1MB), no quality loss. "
            "No watermark, no registration. Fast PDF compressor for all devices."
        ),
        page_keywords=(
            # Primary keywords
            "compress PDF, PDF compressor, compress pdf online free, reduce pdf file size, "
            "shrink pdf, pdf optimizer, make pdf smaller, pdf size reducer, "
            # Size-specific keywords
            "compress pdf to 1mb, compress pdf to 500kb, compress pdf under 10mb, "
            "compress pdf under 25mb gmail, compress pdf for email attachment, "
            "reduce pdf to under 1mb, heavy pdf to small pdf, "
            # Quality keywords
            "compress pdf no quality loss, compress pdf keep quality, compress pdf without blur, "
            "compress pdf high quality, pdf compression best quality, shrink pdf readable, "
            # Use case keywords
            "compress pdf for email, compress pdf for web, compress pdf for printing, "
            "compress scanned pdf, compress pdf images, compress invoice pdf, "
            "compress academic pdf, compress ebook pdf, compress pdf presentation, "
            # Platform keywords
            "compress pdf online, compress pdf mac, compress pdf windows, compress pdf mobile, "
            "compress pdf iphone, compress pdf android, compress pdf from phone, "
            # Free/No registration keywords
            "compress pdf free, compress pdf no registration, compress pdf no watermark, "
            "pdf compressor unlimited, compress pdf safe, compress pdf secure, "
            # Percentage keywords
            "compress pdf 50 percent, compress pdf 90 percent, reduce pdf size by half, "
            # Comparison keywords
            "smallpdf compress alternative, ilovepdf compress alternative, best pdf compressor 2026"
        ),
        page_subtitle=_("Reduce PDF file size without losing quality"),
        header_text=_("Compress PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="compress_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Compress PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Reduce Up to 90%"),
            "description": _(
                "Significantly reduce PDF file size while maintaining readable quality"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Perfect for Email"),
            "description": _(
                "Compress PDFs to under 1MB for email attachments that won't bounce"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Keep Text Sharp"),
            "description": _(
                "Smart compression preserves text clarity while reducing image size"
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>',
            "gradient": "from-amber-500 to-orange-600",
            "title": _("Fast Processing"),
            "description": _(
                "Compress even large PDFs in seconds with our optimized algorithms"
            ),
        },
    ]
    context["benefits_title"] = _("Why Compress PDFs with Convertica?")

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How much can I reduce my PDF file size?"),
            "answer": _(
                "Results vary depending on the content, but you can typically reduce PDF size by 50-90%. "
                "PDFs with many images compress more than text-only documents. "
                "Scanned documents usually achieve the best compression ratios."
            ),
        },
        {
            "question": _("Will compression affect text quality?"),
            "answer": _(
                "No, text remains sharp and readable. Our smart compression algorithm primarily "
                "optimizes images and removes unnecessary metadata while preserving text clarity. "
                "The document remains fully searchable and selectable."
            ),
        },
        {
            "question": _("Can I compress a PDF to exactly 1MB for email?"),
            "answer": _(
                "Our compressor optimizes the file as much as possible while maintaining quality. "
                "For most documents, you'll get a file under 1MB. If the result is still too large, "
                "try splitting the PDF first, then compressing each part."
            ),
        },
        {
            "question": _("Is the compressed PDF still printable?"),
            "answer": _(
                "Yes, compressed PDFs are fully printable. While images are optimized for screen viewing, "
                "text and vector graphics remain at full quality. For high-quality printing needs, "
                "we recommend keeping the original file."
            ),
        },
        {
            "question": _("Can I compress scanned documents?"),
            "answer": _(
                "Yes! Scanned PDFs often benefit the most from compression since they contain large images. "
                "Our tool can significantly reduce the size of scanned documents while keeping "
                "the content readable."
            ),
        },
    ]
    context["faq_title"] = _("Compress PDF - Frequently Asked Questions")

    # SEO Tips
    context["page_tips"] = [
        _("PDFs with images compress better than text-only documents"),
        _("For email attachments, aim for under 10MB (or 25MB for Gmail)"),
        _("If the file is still too large after compression, try splitting it first"),
        _("Scanned documents usually achieve 70-90% size reduction"),
        _("Keep the original file if you need maximum print quality"),
    ]
    context["tips_title"] = _("Tips for PDF Compression")

    # SEO Content
    context["page_content_title"] = _(
        "Compress PDF Online - Reduce File Size Instantly"
    )
    context["page_content_body"] = _(
        "<p>Need to send a large PDF by email? Our <strong>free PDF compressor</strong> "
        "reduces file size significantly while maintaining readable quality. Perfect for "
        "<strong>email attachments, web uploads, and storage optimization</strong>.</p>"
        "<p>The tool uses smart compression algorithms that optimize images and remove unnecessary "
        "metadata while keeping text sharp and documents fully searchable. Most PDFs can be "
        "reduced by <strong>50-90%</strong> in size.</p>"
        "<p><strong>Common uses:</strong> Compress PDFs for email (under 25MB for Gmail), "
        "reduce scanned document sizes, optimize PDFs for website upload, "
        "shrink presentation exports, and prepare files for mobile viewing.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("compress_pdf")
    return render(request, "frontend/pdf_organize/compress_pdf.html", context)


def protect_pdf_page(request):
    """Protect PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Protect PDF with Password - Convertica"),
        page_description=_(
            "Protect PDF files with password encryption. "
            "Secure your PDF documents with strong password protection."
        ),
        page_keywords=(
            # Primary keywords
            "protect PDF, PDF password, encrypt PDF, password protect pdf online free, "
            "pdf security, pdf protection, secure pdf, add password to pdf, "
            # Feature keywords
            "encrypt pdf 256 bit, pdf password protection, pdf encryption tool, "
            "lock pdf with password, pdf owner password, pdf user password, "
            # Use case keywords
            "protect pdf for email, secure pdf for sharing, encrypt confidential pdf, "
            "password protect invoice pdf, secure contract pdf, protect legal documents pdf, "
            "encrypt sensitive pdf, protect financial pdf, secure business pdf, "
            # Restriction keywords
            "prevent pdf printing, prevent pdf copying, restrict pdf editing, "
            "disable pdf printing, pdf copy protection, pdf edit restriction, "
            # Platform keywords
            "protect pdf mac, protect pdf windows, encrypt pdf online, "
            "password pdf mobile, secure pdf iphone, protect pdf android, "
            # Free keywords
            "protect pdf free, encrypt pdf no registration, password pdf no signup, "
            "pdf encryption free online, secure pdf no watermark, "
            # Comparison keywords
            "smallpdf protect alternative, ilovepdf encrypt alternative, adobe encrypt alternative"
        ),
        page_subtitle=_("Secure your PDF documents with password protection"),
        header_text=_("Protect PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="protect_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Protect PDF"),
        select_file_message=_("Please select a PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>',
            "gradient": "from-red-500 to-red-600",
            "title": _("Strong Password Encryption"),
            "description": _(
                "Protect your PDF with industry-standard AES encryption. "
                "Your documents are secured with the password you choose, "
                "preventing unauthorized access."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("User & Owner Passwords"),
            "description": _(
                "Set separate passwords for users and owners. Control who can view, "
                "edit, print, or modify your PDF with different access levels."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Preserve Document Quality"),
            "description": _(
                "Password protection doesn't affect your PDF content. All text, "
                "images, formatting, and document structure remain intact."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Instant Protection"),
            "description": _(
                "Protect your PDF in seconds. Simply upload, set your password, "
                "and download your secured document. No software required."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I protect a PDF with a password?"),
            "answer": _(
                "Upload your PDF file, enter a password in the required field, and click "
                "'Protect PDF'. Your document will be encrypted and can only be opened "
                "with the password you set."
            ),
        },
        {
            "question": _("What's the difference between user and owner passwords?"),
            "answer": _(
                "The user password is required to open and view the PDF. The owner password "
                "allows full access including editing, printing, and copying. If you set both, "
                "users with just the user password have restricted access."
            ),
        },
        {
            "question": _("What encryption is used to protect PDFs?"),
            "answer": _(
                "We use industry-standard AES (Advanced Encryption Standard) encryption "
                "to secure your PDF files. This is the same encryption used by banks and "
                "government agencies."
            ),
        },
        {
            "question": _("Can I remove the password protection later?"),
            "answer": _(
                "Yes, if you know the password, you can use our 'Unlock PDF' tool to remove "
                "the password protection from your PDF document at any time."
            ),
        },
        {
            "question": _("Will I be able to open the protected PDF?"),
            "answer": _(
                "Yes, you can open the protected PDF in any PDF reader (Adobe Reader, Chrome, etc.) "
                "by entering the password. Make sure to save your password in a safe place!"
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "Use a strong password with a mix of letters, numbers, and special characters."
        ),
        _(
            "Write down or securely store your password - we cannot recover it if you forget."
        ),
        _("Use different user and owner passwords for more granular access control."),
        _("Test opening the protected PDF to ensure you remember the password."),
        _(
            "For highly sensitive documents, consider additional security measures beyond encryption."
        ),
    ]

    # SEO Content
    context["page_content_title"] = _(
        "Secure Your PDF Documents with Password Protection"
    )
    context["page_content_body"] = _(
        "<p>Password protecting your PDF documents is essential for maintaining confidentiality "
        "and controlling access to sensitive information. Whether you're sharing financial reports, "
        "legal documents, or personal files, password encryption ensures only authorized people "
        "can access your content.</p>"
        "<p>Our PDF protection tool uses strong AES encryption to secure your documents. "
        "You can set a single password for all access, or configure separate user and owner "
        "passwords to control different levels of access - from viewing only to full editing rights.</p>"
        "<p>Perfect for businesses sharing confidential documents, individuals protecting "
        "personal files, and anyone who needs to control who can access their PDF documents.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("protect_pdf")
    return render(request, "frontend/pdf_security/protect_pdf.html", context)


def unlock_pdf_page(request):
    """Unlock PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Unlock PDF - Remove Password - Convertica"),
        page_description=_(
            "Unlock PDF online free. "
            "Remove password protection from PDF files with the correct password. "
            "Fast PDF unlock tool with no watermark. "
            "Perfect for accessing protected documents. No registration required."
        ),
        page_keywords=(
            "unlock PDF, remove PDF password, unlock pdf online free, "
            "decrypt pdf, pdf unlock, pdf password remover, "
            "unlock pdf no watermark, unlock pdf fast, unlock pdf unlimited, "
            "unlock pdf batch, unlock pdf without losing quality, "
            "unlock pdf maintain quality, unlock pdf safe tool, "
            "pdf unlock for mac online, pdf unlock for mobile, "
            "unlock pdf best 2025, unlock pdf high quality, "
            "unlock pdf for documents, unlock pdf for reports, "
            "pdf unlock google drive safe, pdf unlock cloud tool, "
            "unlock pdf editor included, pdf unlock without errors, "
            "unlock pdf all pages, unlock pdf specific pages, "
            "pdf unlock for students, free pdf unlock tool safe, "
            "unlock pdf without registration, pdf unlock one click, "
            "unlock pdf with password, remove pdf password protection, "
            "decrypt pdf file, unlock encrypted pdf, pdf password removal, "
            "unlock protected pdf, remove pdf restrictions, "
            "unlock pdf for invoices, unlock pdf for legal documents"
        ),
        page_subtitle=_("Remove password protection from your PDF"),
        header_text=_("Unlock PDF"),
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="unlock_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text=_("Unlock PDF"),
        select_file_message=_("Please select a password-protected PDF file."),
    )

    # SEO Benefits
    context["page_benefits"] = [
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>',
            "gradient": "from-green-500 to-green-600",
            "title": _("Remove Password Protection"),
            "description": _(
                "Easily remove password protection from your PDF files. Enter the correct "
                "password and get an unlocked PDF that can be opened without restrictions."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>',
            "gradient": "from-blue-500 to-blue-600",
            "title": _("Secure & Private"),
            "description": _(
                "Your PDF files are processed securely. We don't store your documents "
                "or passwords. Files are automatically deleted after processing."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>',
            "gradient": "from-purple-500 to-purple-600",
            "title": _("Preserve Document Quality"),
            "description": _(
                "Unlocking doesn't affect your PDF content. All text, images, "
                "formatting, and document structure remain exactly the same."
            ),
        },
        {
            "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
            "gradient": "from-yellow-500 to-orange-500",
            "title": _("Instant Unlocking"),
            "description": _(
                "Remove password protection in seconds. Upload your PDF, enter "
                "the password, and download your unlocked document immediately."
            ),
        },
    ]

    # SEO FAQ
    context["page_faq"] = [
        {
            "question": _("How do I unlock a password-protected PDF?"),
            "answer": _(
                "Upload your password-protected PDF, enter the correct password in the "
                "provided field, and click 'Unlock PDF'. The password protection will be "
                "removed and you can download an unlocked version."
            ),
        },
        {
            "question": _("Can I unlock a PDF without knowing the password?"),
            "answer": _(
                "No, you must know the correct password to unlock the PDF. This tool removes "
                "password protection from PDFs when you provide the correct password. "
                "We cannot bypass or crack PDF passwords."
            ),
        },
        {
            "question": _("What types of PDF protection can this tool remove?"),
            "answer": _(
                "This tool removes password protection that requires a password to open the PDF. "
                "Once unlocked, the PDF can be opened, viewed, printed, and edited without "
                "any restrictions."
            ),
        },
        {
            "question": _("Is my PDF and password secure?"),
            "answer": _(
                "Yes, your files and passwords are processed securely and are not stored on "
                "our servers. All data is automatically deleted after processing. We use "
                "encrypted connections to protect your information."
            ),
        },
        {
            "question": _("Will the unlocked PDF work on all devices?"),
            "answer": _(
                "Yes, the unlocked PDF is a standard PDF file that can be opened in any "
                "PDF reader on any device - computers, tablets, and smartphones. "
                "No special software is required."
            ),
        },
    ]

    # SEO Tips
    context["page_tips"] = [
        _(
            "Make sure you have the correct password before attempting to unlock the PDF."
        ),
        _(
            "If you've forgotten the password, contact the person who created the protected PDF."
        ),
        _(
            "After unlocking, you can use our Protect PDF tool to set a new password if needed."
        ),
        _("Unlocked PDFs can be edited, printed, and shared without restrictions."),
        _("Keep a backup of your original protected PDF in case you need it later."),
    ]

    # SEO Content
    context["page_content_title"] = _("Remove Password Protection from Your PDF Files")
    context["page_content_body"] = _(
        "<p>Unlock password-protected PDF files quickly and easily when you have the correct "
        "password. Our PDF unlock tool removes the password requirement, giving you a PDF "
        "that can be opened, edited, and shared without entering a password each time.</p>"
        "<p>This tool is perfect when you have a legitimately protected PDF and want to "
        "remove the password for easier access. Whether you've received protected documents "
        "from colleagues, downloaded secured files, or want to remove protection from your "
        "own PDFs, our tool makes the process simple.</p>"
        "<p>Note: This tool requires you to know the correct password. It does not bypass "
        "or crack password protection - it simply removes the password requirement from "
        "PDFs when you provide the valid password.</p>"
    )

    # Related tools for internal linking
    context["related_tools"] = _get_related_tools("unlock_pdf")
    return render(request, "frontend/pdf_security/unlock_pdf.html", context)


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


@vary_on_cookie
@cache_page(60 * 60 * 24 * 7)
def terms_page(request):
    """Terms of Service page."""
    page_title = _("Terms of Service - Convertica")
    page_description = _(
        "Read Convertica's Terms of Service. "
        "Understand the terms and conditions for using our PDF tools and services."
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
    }

    return render(request, "frontend/contact.html", context)


@vary_on_cookie
@cache_page(60 * 60 * 24)
@ensure_csrf_cookie
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
        {"url": "all-tools/", "priority": "0.9", "changefreq": "weekly"},
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
            f"{base_url}/"
            if page_url == "" and lang == default_language
            else (
                f"{base_url}/{lang}/"
                if page_url == ""
                else f"{base_url}/{lang}/{page_url}"
            )
        )

        xml += "  <url>\n"
        xml += f"    <loc>{url}</loc>\n"
        xml += f"    <lastmod>{current_date}</lastmod>\n"
        xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{page["priority"]}</priority>\n'

        for alt_lang_code, _ in languages:
            alt_url = (
                f"{base_url}/"
                if page_url == "" and alt_lang_code == default_language
                else (
                    f"{base_url}/{alt_lang_code}/"
                    if page_url == ""
                    else f"{base_url}/{alt_lang_code}/{page_url}"
                )
            )
            xml += (
                f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" href="{alt_url}"/>'
                + "\n"
            )

        default_url = (
            f"{base_url}/"
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
                slug__in=["daily-hero", "monthly-hero", "yearly-hero"],
                is_active=True,
            )
            .only("slug", "price", "currency", "duration_days")
            .all()
        )
        plans_by_slug = {p.slug: p for p in plans}

        context["daily_plan"] = plans_by_slug.get("daily-hero")
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
