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

from utils_site.src.api.conversion_limits import MAX_PDF_PAGES


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
        "max_pages": MAX_PDF_PAGES,
    }


def pdf_to_word_page(request):
    """PDF to Word conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to Word - Convertica"),
        page_description=_(
            "Convert PDF to Word online free without losing formatting. "
            "Fast PDF to DOCX converter with no email required, unlimited conversions, "
            "high-quality output. Perfect for documents, resumes, and business files. "
            "No registration needed."
        ),
        page_keywords=(
            "PDF to Word, convert PDF to Word online free, "
            "PDF to DOCX, PDF to Word converter, "
            "convert PDF to Word without losing formatting, "
            "PDF to Word no email required, unlimited PDF to Word conversion"
            "pdf to word converter clean layout, pdf to word converter best 2025, "
            "pdf to word converter high accuracy, pdf to word converter for mac online, "
            "pdf to word for linux online, pdf to word converter for students, "
            "free pdf to word tool safe, pdf to word without registration, "
            "pdf to word one click, convert locked pdf to word, "
            "pdf to word keep images, pdf to word high resolution, "
            "pdf to word for legal documents, pdf to word for invoice, "
            "pdf to word maintain formatting, pdf to word google drive safe, "
            "pdf to word cloud converter, pdf to word export text only, "
            "pdf text to word converter, pdf to word editor included, "
            "pdf to doc converter without errors, best ocr pdf to word free, "
            "extract text from pdf to word, scanned image pdf to docx, "
            "pdf to word converter for handwriting, convert pdf article to word, "
            "convert pdf chapters to word, pdf to word export without tables mess, "
            "pdf to word italics preserved, pdf to word job application, "
            "pdf to word academic paper, pdf to word bibliography correct, "
            "pdf to word table alignment maintained, pdf to word hyperlinked text preserved"
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
    return render(request, "frontend/pdf_convert/pdf_to_word.html", context)


def word_to_pdf_page(request):
    """Word to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("Word to PDF - Convertica"),
        page_description=_(
            "Convert Word to PDF online free without losing formatting. "
            "Fast DOCX to PDF converter with no email required, unlimited conversions, "
            "high-quality output. Perfect for documents, resumes, and business files. "
            "No registration needed."
        ),
        page_keywords=(
            "Word to PDF, DOCX to PDF, DOC to PDF, convert Word to PDF online free, "
            "word to pdf without losing formatting, docx to pdf converter no email, "
            "word to pdf fast online, convert word document to pdf, "
            "docx to pdf online free, word to pdf converter unlimited, "
            "word to pdf converter no sign up, convert doc to pdf online, "
            "word to pdf export free, word to pdf maintain formatting, "
            "word to pdf high quality, convert word resume to pdf, "
            "word to pdf batch converter, convert multiple word to pdf online, "
            "word to pdf no ads, word to pdf no virus, "
            "word to pdf converter small file, word to pdf converter large file, "
            "word to pdf converter clean layout, word to pdf converter best 2025, "
            "word to pdf converter high accuracy, word to pdf converter for mac online, "
            "word to pdf for linux online, word to pdf converter for students, "
            "free word to pdf tool safe, word to pdf without registration, "
            "word to pdf one click, convert locked word to pdf, "
            "word to pdf keep images, word to pdf high resolution, "
            "word to pdf for legal documents, word to pdf for invoice, "
            "word to pdf google drive safe, word to pdf cloud converter, "
            "word to pdf export text only, word text to pdf converter, "
            "word to pdf editor included, doc to pdf converter without errors, "
            "convert word article to pdf, convert word chapters to pdf, "
            "word to pdf italics preserved, word to pdf job application, "
            "word to pdf academic paper, word to pdf bibliography correct, "
            "word to pdf table alignment maintained, word to pdf hyperlinked text preserved"
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
    return render(request, "frontend/pdf_convert/word_to_pdf.html", context)


def pdf_to_jpg_page(request):
    """PDF to JPG conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("PDF to JPG - Convertica"),
        page_description=_(
            "Convert PDF to JPG online free with high quality. "
            "PDF to image converter with no watermark, high resolution (300-600 DPI), "
            "batch conversion. Extract images from PDF or convert PDF pages to JPG/PNG. "
            "Perfect for printing, web upload, and social media."
        ),
        page_keywords=(
            "PDF to JPG, PDF to image, pdf to jpg online free, "
            "pdf to png converter high quality, pdf to image no watermark, "
            "pdf to jpg high resolution, batch pdf to jpg converter, "
            "convert pdf page to image free, pdf to jpg without losing quality, "
            "pdf to png transparent background, pdf to jpg best quality online, "
            "pdf to png converter free tool, export pdf pages as images, "
            "convert scanned pdf to png, pdf to jpg for printing, "
            "pdf to jpg hd converter, pdf to image converter 300 dpi, "
            "600 dpi pdf to jpg converter, convert pdf drawings to images, "
            "convert pdf slides to images, pdf to jpg converter no ads, "
            "pdf to jpg unlimited free, pdf to jpg convert specific pages, "
            "pdf to image for mobile, pdf to image for instagram, "
            "pdf to image crop free, pdf to png crisp text, "
            "pdf to jpg converter for mac online, pdf to jpg convert all pages, "
            "pdf to image converter fast, pdf to image converter lightweight, "
            "convert pdf book to images, pdf diagrams to jpg free, "
            "extract pdf page as png, pdf to jpg converter with compression, "
            "convert pdf floor plans to jpg, pdf artwork to high-res images, "
            "pdf poster to jpg, pdf brochure to images, "
            "pdf to jpg for website upload, pdf to jpg text readable, "
            "pdf single page to jpg free"
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
    return render(request, "frontend/pdf_convert/pdf_to_jpg.html", context)


def jpg_to_pdf_page(request):
    """JPG to PDF conversion page."""
    context = _get_converter_context(
        request,
        page_title=_("JPG to PDF - Convertica"),
        page_description=_(
            "Convert JPG to PDF online free without compression. "
            "Merge multiple images into one PDF, combine photos to PDF, "
            "create PDF from images with high resolution. "
            "Perfect for documents, receipts, homework, and university submissions. "
            "No watermark, unlimited conversions."
        ),
        page_keywords=(
            "JPG to PDF, image to PDF, jpg to pdf online free, "
            "png to pdf without compression, jpg to pdf merge multiple images, "
            "convert photos to pdf, jpg to pdf no watermark, "
            "image to pdf converter with margins, image to pdf high resolution, "
            "convert scanned photos to pdf, jpg to pdf for a4 format, "
            "multiple scans to pdf, png to pdf transparent background fix, "
            "jpg to pdf sharp quality, image to pdf fast conversion, "
            "combine images into one pdf, jpg to pdf converter for documents, "
            "png to pdf no ads, jpg to pdf converter unlimited, "
            "image to pdf for mobile upload, create pdf from images free, "
            "images to pdf without white borders, png to pdf maintain quality, "
            "jpg to pdf converter batch mode, convert drawings to pdf, "
            "convert screenshots to pdf, image to pdf converter for receipts, "
            "convert notes photos to pdf, image to pdf auto rotate, "
            "image to pdf correct orientation, png to pdf high-dpi, "
            "jpg to pdf file size small, large images to pdf converter, "
            "convert passport photo to pdf, combine photos to pdf online, "
            "jpg to pdf for homework, jpg to pdf for university submission, "
            "png to pdf color accurate, png to pdf flatten layers, "
            "image to pdf converter drag and drop, photos to pdf reorder pages, "
            "convert artwork scans to pdf"
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
            "rotate PDF, PDF rotation, rotate pdf online free, "
            "rotate pdf pages 90 degrees, rotate pdf pages 180 degrees, "
            "rotate pdf pages 270 degrees, pdf rotation tool no watermark, "
            "rotate pdf fast online, rotate pdf batch, rotate multiple pdf pages, "
            "rotate pdf without losing quality, rotate scanned pdf, "
            "rotate pdf for printing, pdf rotation tool unlimited, "
            "rotate pdf no ads, rotate pdf safe tool, pdf rotation for mac online, "
            "pdf rotation for mobile, rotate pdf and save, "
            "pdf rotation maintain quality, rotate pdf pages clockwise, "
            "rotate pdf pages counterclockwise, fix pdf orientation, "
            "correct pdf page orientation, rotate pdf document, "
            "pdf rotation tool best 2025, rotate pdf high quality, "
            "rotate pdf for documents, rotate pdf for invoices, "
            "rotate pdf for reports, rotate pdf google drive safe, "
            "pdf rotation cloud tool, rotate pdf editor included, "
            "rotate pdf without errors, rotate pdf pages individually, "
            "rotate pdf all pages, rotate pdf specific pages, "
            "pdf rotation for students, free pdf rotation tool safe, "
            "rotate pdf without registration, rotate pdf one click"
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
    return render(request, "frontend/pdf_edit/rotate_pdf.html", context)


def add_page_numbers_page(request):
    """Add page numbers to PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Add Page Numbers to PDF - Convertica"),
        page_description=_(
            "Add page numbers to PDF online free with customizable position, "
            "font size, and format. Fast PDF page numbering tool with no watermark. "
            "Perfect for documents, reports, and academic papers. No registration required."
        ),
        page_keywords=(
            "add page numbers PDF, PDF page numbers, "
            "add page numbers to pdf online free, number pdf pages, "
            "pdf page numbering tool, add page numbers pdf no watermark, "
            "pdf page numbers custom position, pdf page numbers font size, "
            "pdf page numbers format, add page numbers pdf fast, "
            "pdf page numbering unlimited, add page numbers pdf no ads, "
            "pdf page numbers for documents, pdf page numbers for reports, "
            "pdf page numbers for academic papers, add page numbers pdf batch, "
            "pdf page numbering maintain quality, add page numbers pdf safe tool, "
            "pdf page numbers top, pdf page numbers bottom, "
            "pdf page numbers center, pdf page numbers left, "
            "pdf page numbers right, add page numbers pdf for mac online, "
            "add page numbers pdf for mobile, pdf page numbering best 2025, "
            "add page numbers pdf high quality, pdf page numbers for students, "
            "free pdf page numbering tool safe, add page numbers pdf without registration, "
            "pdf page numbering one click, add page numbers pdf google drive safe, "
            "pdf page numbering cloud tool, add page numbers pdf editor included, "
            "pdf page numbers without errors, add page numbers pdf all pages, "
            "add page numbers pdf specific pages, pdf page numbering for invoices, "
            "pdf page numbers for legal documents"
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
    return render(request, "frontend/pdf_edit/add_page_numbers.html", context)


def add_watermark_page(request):
    """Add watermark to PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Add Watermark to PDF - Convertica"),
        page_description=_(
            "Add watermark to PDF online free with text or image. "
            "Customize position, transparency, and size. "
            "Fast PDF watermarking tool with no watermark on tool itself. "
            "Perfect for document protection and branding. No registration required."
        ),
        page_keywords=(
            "add watermark PDF, PDF watermark, "
            "add watermark to pdf online free, watermark pdf documents, "
            "pdf watermarking tool, add text watermark to pdf, "
            "add image watermark to pdf, pdf watermark custom position, "
            "pdf watermark transparency, pdf watermark size, "
            "add watermark pdf no watermark, pdf watermarking unlimited, "
            "add watermark pdf fast, pdf watermark for documents, "
            "pdf watermark for protection, pdf watermark for branding, "
            "add watermark pdf batch, pdf watermarking maintain quality, "
            "add watermark pdf safe tool, pdf watermark top, "
            "pdf watermark bottom, pdf watermark center, pdf watermark diagonal, "
            "add watermark pdf for mac online, add watermark pdf for mobile, "
            "pdf watermarking best 2025, add watermark pdf high quality, "
            "pdf watermark for students, free pdf watermarking tool safe, "
            "add watermark pdf without registration, pdf watermarking one click, "
            "add watermark pdf google drive safe, pdf watermarking cloud tool, "
            "add watermark pdf editor included, pdf watermark without errors, "
            "add watermark pdf all pages, add watermark pdf specific pages, "
            "pdf watermark for invoices, pdf watermark for legal documents, "
            "pdf watermark text, pdf watermark image, pdf watermark logo"
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
    return render(request, "frontend/pdf_edit/add_watermark.html", context)


def crop_pdf_page(request):
    """Crop PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Crop PDF - Convertica"),
        page_description=_(
            "Crop PDF pages online free with precise crop box coordinates. "
            "Fast PDF cropping tool with no watermark, visual editor, "
            "and quality preservation. Perfect for removing margins and "
            "unwanted content. No registration required."
        ),
        page_keywords=(
            "crop PDF, PDF crop, crop pdf online free, "
            "crop pdf pages, pdf cropping tool, crop pdf with visual editor, "
            "crop pdf precise coordinates, crop pdf remove margins, "
            "crop pdf unwanted content, crop pdf fast online, "
            "pdf cropping no watermark, crop pdf unlimited, crop pdf batch, "
            "crop pdf without losing quality, crop pdf maintain quality, "
            "crop pdf safe tool, pdf cropping for mac online, "
            "pdf cropping for mobile, crop pdf and save, "
            "pdf cropping best 2025, crop pdf high quality, "
            "crop pdf for documents, crop pdf for printing, "
            "crop pdf for scanning, pdf cropping google drive safe, "
            "pdf cropping cloud tool, crop pdf editor included, "
            "pdf cropping without errors, crop pdf all pages, "
            "crop pdf specific pages, pdf cropping for students, "
            "free pdf cropping tool safe, crop pdf without registration, "
            "pdf cropping one click, crop pdf pages individually, "
            "crop pdf custom size, pdf cropping for invoices, "
            "pdf cropping for reports"
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
    return render(request, "frontend/pdf_edit/crop_pdf.html", context)


def merge_pdf_page(request):
    """Merge PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Merge PDF - Convertica"),
        page_description=_(
            "Merge PDF online free without watermark. "
            "Combine two PDFs into one, merge multiple PDF files fast, "
            "preserve bookmarks and quality. Unlimited PDF merger with "
            "drag and drop. No registration required."
        ),
        page_keywords=(
            "merge PDF, combine PDF, merge pdf online free, "
            "combine two pdfs into one, merge pdf without watermark, "
            "pdf merger unlimited, combine pdf pages in order, "
            "merge multiple pdf files fast, merge pdf and preserve bookmarks, "
            "merge pdf no quality loss, pdf merge no ads, "
            "join pdf files secure, merge pdf large files, "
            "merge pdf drag and drop, combine pdf forms, "
            "merge pdf thesis chapters, merge pdf scanned pages, "
            "merge pdf double sided documents, merge pdf and reorder pages, "
            "merge protected pdfs, combine pdf receipts, "
            "merge pdf into single long file, merge pdf business documents, "
            "combine pdf statements, merge pdf drawings, merge pdf invoices, "
            "combine pdf lecture notes, merge pdf with table of contents, "
            "merge pdf into booklet, combine pdf without duplicates, "
            "merge pdf and compress, batch merge pdf online"
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
    return render(request, "frontend/pdf_organize/merge_pdf.html", context)


def split_pdf_page(request):
    """Split PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Split PDF - Convertica"),
        page_description=_(
            "Split PDF online free by pages, ranges, or bookmarks. "
            "Extract specific pages from PDF, remove pages, "
            "divide PDF into multiple files. Fast PDF splitter with no watermark. "
            "No registration required."
        ),
        page_keywords=(
            "split PDF, divide PDF, split pdf online free, "
            "split pdf by pages, separate pdf into pages, "
            "pdf splitter no watermark, extract pages from pdf free, "
            "split pdf without losing quality, pdf splitter unlimited, "
            "extract specific pages pdf, split pdf by range online, "
            "split pdf every page, divide pdf into multiple files, "
            "pdf splitter with reorder, remove page from pdf online, "
            "delete pages from pdf free, split large pdf quickly, "
            "split pdf fast tool, extract pdf chapters, "
            "extract pdf table only, extract pdf images only, "
            "split pdf scanned file, extract odd pages pdf, "
            "extract even pages pdf, split pdf no ads, "
            "split pdf safe tool, separate pdf forms, "
            "pdf splitter for mac online, pdf splitter for mobile, "
            "extract pdf page to new file, pdf divider high quality, "
            "cut pdf into parts, remove front page pdf, "
            "remove blank pages pdf, split pdf school document, "
            "extract thesis pages pdf, extract invoice pages pdf, "
            "extract pdf long report, extract pdf cover page, "
            "pdf split maintain orientation, pdf split keep metadata, "
            "split pdf by bookmarks, pdf split by file size, "
            "split pdf for printing, extract pdf appendix, "
            "extract pdf annex, extract pdf diagrams, "
            "extract confidential pages pdf, split pdf interview transcript, "
            "cut pdf into equal parts, split scanned pdf pages"
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
    return render(request, "frontend/pdf_organize/split_pdf.html", context)


def remove_pages_page(request):
    """Remove pages from PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Remove Pages from PDF - Convertica"),
        page_description=_(
            "Remove pages from PDF online free. "
            "Delete unwanted pages quickly and easily with no watermark. "
            "Fast PDF page removal tool. Perfect for cleaning up documents. "
            "No registration required."
        ),
        page_keywords=(
            "remove PDF pages, delete PDF pages, "
            "remove pages from pdf online free, delete pdf pages, "
            "pdf page remover, remove pdf pages no watermark, "
            "delete pdf pages fast, remove pdf pages unlimited, "
            "remove pdf pages batch, remove pdf pages without losing quality, "
            "remove pdf pages maintain quality, remove pdf pages safe tool, "
            "pdf page removal for mac online, pdf page removal for mobile, "
            "remove pdf pages best 2025, remove pdf pages high quality, "
            "remove pdf pages for documents, remove pdf pages for reports, "
            "pdf page removal google drive safe, pdf page removal cloud tool, "
            "remove pdf pages editor included, pdf page removal without errors, "
            "remove pdf pages all pages, remove pdf pages specific pages, "
            "pdf page removal for students, free pdf page removal tool safe, "
            "remove pdf pages without registration, pdf page removal one click, "
            "remove pdf pages individually, remove pdf pages custom selection, "
            "pdf page removal for invoices, pdf page removal for legal documents"
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
    return render(request, "frontend/pdf_organize/remove_pages.html", context)


def extract_pages_page(request):
    """Extract pages from PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Extract Pages from PDF - Convertica"),
        page_description=_(
            "Extract pages from PDF online free. "
            "Select and extract specific pages to create a new PDF. "
            "Fast PDF page extraction tool with no watermark. "
            "Perfect for creating custom documents. No registration required."
        ),
        page_keywords=(
            "extract PDF pages, PDF page extractor, "
            "extract pages from pdf online free, select pdf pages, "
            "pdf page extraction tool, extract pdf pages no watermark, "
            "extract pdf pages fast, extract pdf pages unlimited, "
            "extract pdf pages batch, extract pdf pages without losing quality, "
            "extract pdf pages maintain quality, extract pdf pages safe tool, "
            "pdf page extraction for mac online, pdf page extraction for mobile, "
            "extract pdf pages best 2025, extract pdf pages high quality, "
            "extract pdf pages for documents, extract pdf pages for reports, "
            "pdf page extraction google drive safe, pdf page extraction cloud tool, "
            "extract pdf pages editor included, pdf page extraction without errors, "
            "extract pdf pages all pages, extract pdf pages specific pages, "
            "extract pdf pages by range, extract pdf pages individually, "
            "pdf page extraction for students, free pdf page extraction tool safe, "
            "extract pdf pages without registration, pdf page extraction one click, "
            "extract pdf pages custom selection, pdf page extraction for invoices, "
            "pdf page extraction for legal documents"
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
    return render(request, "frontend/pdf_organize/extract_pages.html", context)


def organize_pdf_page(request):
    """Organize PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Organize PDF - Convertica"),
        page_description=_(
            "Organize PDF online free. "
            "Reorder pages, sort content, and manage your PDF files "
            "with drag and drop. Fast PDF organizer with no watermark. "
            "Perfect for organizing documents and reports. No registration required."
        ),
        page_keywords=(
            "organize PDF, PDF organizer, organize pdf online free, "
            "reorder pdf pages, pdf page organizer, organize pdf documents, "
            "reorder pdf pages drag and drop, organize pdf pages sort, "
            "organize pdf content, organize pdf fast, pdf organizer no watermark, "
            "organize pdf unlimited, organize pdf batch, "
            "organize pdf without losing quality, organize pdf maintain quality, "
            "organize pdf safe tool, pdf organizer for mac online, "
            "pdf organizer for mobile, organize pdf and save, "
            "pdf organizer best 2025, organize pdf high quality, "
            "organize pdf for documents, organize pdf for reports, "
            "organize pdf for scanning, pdf organizer google drive safe, "
            "pdf organizer cloud tool, organize pdf editor included, "
            "pdf organizer without errors, organize pdf all pages, "
            "organize pdf specific pages, pdf organizer for students, "
            "free pdf organizer tool safe, organize pdf without registration, "
            "pdf organizer one click, organize pdf pages individually, "
            "organize pdf custom order, pdf organizer for invoices, "
            "pdf organizer for legal documents"
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
            "PDF to PowerPoint, PDF to PPT, PDF to PPTX, convert PDF to PowerPoint online free, "
            "pdf to ppt without losing formatting, pdf to powerpoint converter, "
            "pdf to pptx converter no email, pdf to ppt fast online, "
            "convert pdf slides to powerpoint, pdf to pptx online free, "
            "pdf to ppt converter unlimited, pdf to ppt converter no sign up, "
            "pdf to powerpoint high quality, pdf to ppt for presentations"
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
            "PDF to HTML, convert PDF to HTML online free, "
            "pdf to html converter, pdf to html with images, "
            "pdf to html converter no email, pdf to html fast online, "
            "extract pdf to html, pdf to html online free, "
            "pdf to html converter unlimited, pdf to html converter no sign up, "
            "pdf to html high quality, pdf to html for web"
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
    return render(request, "frontend/pdf_convert/pdf_to_html.html", context)


def compress_pdf_page(request):
    """Compress PDF page."""
    context = _get_converter_context(
        request,
        page_title=_("Compress PDF - Convertica"),
        page_description=_(
            "Compress PDF online free to reduce file size fast. "
            "PDF compressor with no watermark, compress PDF to under 1MB for email, "
            "reduce PDF file size without losing quality. Best PDF compression tool 2025."
        ),
        page_keywords=(
            "compress PDF, PDF compressor, compress pdf online free, "
            "pdf compressor no watermark, reduce pdf file size fast, "
            "compress pdf for email, compress pdf to under 1mb, "
            "compress pdf to under 500kb, heavy pdf to small pdf, "
            "compress scanned pdf, pdf optimizer without quality loss, "
            "compress pdf images, shrink pdf without losing text clarity, "
            "pdf compressor easy, compress pdf batch, compress large pdf files, "
            "best pdf compression online, compress pdf for web upload, "
            "compress academic pdf, compress invoice pdf, "
            "compress color pdf, compress black and white pdf, "
            "compress pdf drawings, reduce pdf scan heavy images, "
            "compress pdf for mobile, pdf compression fast tool, "
            "compress pdf up to 90 percent, compress pdf animation included, "
            "compress graphics-heavy pdf, compress powerpoint exported pdf, "
            "compress ebook pdf, compress pdf keep quality, "
            "compress pdf ultra small, reduce pdf dpi free, "
            "convert and compress pdf, compress pdf from phone, "
            "compress pdf safe no upload, compress confidential pdf, "
            "compress pdf for printing, compress scanned docs pdf, "
            "reduce pdf file email limit, compress pdf reduce blur"
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
            "protect PDF, PDF password, encrypt PDF, "
            "PDF security, PDF protection, secure PDF"
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
