# utils_site/src/frontend/views.py

from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods


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

    context = {
        "page_title": _("Convertica – Online PDF ↔ Word Converter"),
        "page_description": _(
            "Fast, simple and secure online PDF to Word and Word to PDF converter. Convert documents instantly, no registration required."
        ),
        "page_keywords": _(
            "PDF to Word, Word to PDF, PDF converter, DOCX converter, online converter, free converter, convert PDF, convert Word, free pdf tools online, pdf tools no registration, best pdf converter online, pdf editor online free, pdf tools for students, pdf tools for business, smallpdf alternative, ilovepdf alternative, adobe acrobat alternative, free pdf converter, pdf merger online, pdf splitter online, pdf compressor online, pdf rotator online, pdf watermark tool, high quality pdf converter, pdf converter no quality loss, pdf converter best quality, pdf converter for mac, pdf converter for windows, pdf converter for linux, pdf converter mobile"
        ),
        "latest_articles": latest_articles,
    }
    return render(request, "frontend/index.html", context)


def _get_converter_context(
    page_title_key: str,
    page_description_key: str,
    page_keywords_key: str,
    page_subtitle_key: str,
    header_text_key: str,
    file_input_name: str,
    file_accept: str,
    api_url_name: str,
    replace_regex: str,
    replace_to: str,
    button_text_key: str,
    select_file_message_key: str,
    button_class: str = "bg-blue-600 text-white hover:bg-blue-700",
) -> dict:
    """Helper function to generate converter page context.

    Args:
        page_title_key: Translation key for page title
        page_description_key: Translation key for page description
        page_keywords_key: Translation key for page keywords (English keywords, not translated for SEO)
        page_subtitle_key: Translation key for page subtitle
        header_text_key: Translation key for header text
        file_input_name: Name of the file input field
        file_accept: Accepted file extensions (e.g., '.pdf' or '.doc,.docx')
        api_url_name: Name of the API URL pattern
        replace_regex: Regex pattern for filename replacement
        replace_to: Replacement string for filename
        button_text_key: Translation key for button text
        select_file_message_key: Translation key for select file message
        button_class: CSS classes for the convert button

    Returns:
        dict: Context dictionary for the template
    """

    # Keywords are kept in English for SEO (users search in English even in other countries)
    # But we can add language-specific keywords if needed
    # current_lang = get_language()  # Not used currently, but may be needed in future
    # For now, keywords remain in English for all languages (better for SEO)
    # If needed, we can add language-specific keywords here
    keywords = page_keywords_key

    return {
        "page_title": _(page_title_key),
        "page_description": _(page_description_key),
        "page_keywords": keywords,  # Keep English keywords for SEO
        "page_subtitle": _(page_subtitle_key),
        "header_text": _(header_text_key),
        "file_input_name": file_input_name,
        "file_accept": file_accept,
        "button_class": button_class,
        "button_text": _(button_text_key),
        "select_file_message": _(select_file_message_key),
        "api_url": reverse(api_url_name),
        "replace_regex": replace_regex,
        "replace_to": replace_to,
        "error_message": _("Conversion failed. Please try again."),
    }


def pdf_to_word_page(request):
    """PDF to Word conversion page."""
    context = _get_converter_context(
        page_title_key="PDF to Word - Convertica",
        page_description_key="Convert PDF to Word online free without losing formatting. Fast PDF to DOCX converter with no email required, unlimited conversions, high-quality output. Perfect for students, professionals, and businesses. No registration needed.",
        page_keywords_key="PDF to Word, PDF to DOCX, convert PDF to Word online free, pdf to word without losing formatting, pdf to word converter no email, pdf to word fast online, pdf to editable word free, pdf to docx converter online, scanned pdf to word ocr free, convert protected pdf to word, pdf to word converter without watermark, pdf to word mobile friendly, pdf to word best quality, how to convert pdf to word without adobe, pdf to word converter unlimited, pdf to word converter no sign up, pdf to doc online converter, pdf to word export free, pdf form to word converter, pdf table to word online, convert pdf resume to word, pdf to word batch converter, convert multiple pdf to word online, pdf to word no ads, pdf to word no virus, pdf to word converter with ocr, pdf to word converter small file, pdf to word converter large file, pdf to word converter clean layout, pdf to word converter best 2025, pdf to word converter high accuracy, pdf to word converter for mac online, pdf to word for linux online, pdf to word converter for students, free pdf to word tool safe, pdf to word without registration, pdf to word one click, convert locked pdf to word, pdf to word keep images, pdf to word high resolution, pdf to word for legal documents, pdf to word for invoice, pdf to word maintain formatting, pdf to word google drive safe, pdf to word cloud converter, pdf to word export text only, pdf text to word converter, pdf to word editor included, pdf to doc converter without errors, best ocr pdf to word free, extract text from pdf to word, scanned image pdf to docx, pdf to word converter for handwriting, convert pdf article to word, convert pdf chapters to word, pdf to word export without tables mess, pdf to word italics preserved, pdf to word job application, pdf to word academic paper, pdf to word bibliography correct, pdf to word table alignment maintained, pdf to word hyperlinked text preserved",
        page_subtitle_key="Convert your PDF documents to editable Word format in seconds",
        header_text_key="PDF to Word Converter",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_word_api",
        replace_regex=r"\.pdf$",
        replace_to=".docx",
        button_text_key="Convert PDF to Word",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/converter_generic.html", context)


def word_to_pdf_page(request):
    """Word to PDF conversion page."""
    context = _get_converter_context(
        page_title_key="Word to PDF - Convertica",
        page_description_key="Convert Word to PDF online free without losing formatting. Fast DOCX to PDF converter with no email required, unlimited conversions, high-quality output. Perfect for documents, resumes, and business files. No registration needed.",
        page_keywords_key="Word to PDF, DOCX to PDF, DOC to PDF, convert Word to PDF online free, word to pdf without losing formatting, docx to pdf converter no email, word to pdf fast online, convert word document to pdf, docx to pdf online free, word to pdf converter unlimited, word to pdf converter no sign up, convert doc to pdf online, word to pdf export free, word to pdf maintain formatting, word to pdf high quality, convert word resume to pdf, word to pdf batch converter, convert multiple word to pdf online, word to pdf no ads, word to pdf no virus, word to pdf converter small file, word to pdf converter large file, word to pdf converter clean layout, word to pdf converter best 2025, word to pdf converter high accuracy, word to pdf converter for mac online, word to pdf for linux online, word to pdf converter for students, free word to pdf tool safe, word to pdf without registration, word to pdf one click, convert locked word to pdf, word to pdf keep images, word to pdf high resolution, word to pdf for legal documents, word to pdf for invoice, word to pdf google drive safe, word to pdf cloud converter, word to pdf export text only, word text to pdf converter, word to pdf editor included, doc to pdf converter without errors, convert word article to pdf, convert word chapters to pdf, word to pdf italics preserved, word to pdf job application, word to pdf academic paper, word to pdf bibliography correct, word to pdf table alignment maintained, word to pdf hyperlinked text preserved",
        page_subtitle_key="Convert your Word documents to PDF format in seconds",
        header_text_key="Word to PDF Converter",
        file_input_name="word_file",
        file_accept=".doc,.docx",
        api_url_name="word_to_pdf_api",
        replace_regex=r"\.(docx?|DOCX?)$",
        replace_to=".pdf",
        button_text_key="Convert to PDF",
        select_file_message_key="Please select a Word file.",
    )
    return render(request, "frontend/converter_generic.html", context)


def pdf_to_jpg_page(request):
    """PDF to JPG conversion page."""
    context = _get_converter_context(
        page_title_key="PDF to JPG - Convertica",
        page_description_key="Convert PDF to JPG online free with high quality. PDF to image converter with no watermark, high resolution (300-600 DPI), batch conversion. Extract images from PDF or convert PDF pages to JPG/PNG. Perfect for printing, web upload, and social media.",
        page_keywords_key="PDF to JPG, PDF to image, pdf to jpg online free, pdf to png converter high quality, pdf to image no watermark, pdf to jpg high resolution, batch pdf to jpg converter, convert pdf page to image free, pdf to jpg without losing quality, pdf to png transparent background, pdf to jpg best quality online, pdf to png converter free tool, export pdf pages as images, convert scanned pdf to png, pdf to jpg for printing, pdf to jpg hd converter, pdf to image converter 300 dpi, 600 dpi pdf to jpg converter, convert pdf drawings to images, convert pdf slides to images, pdf to jpg converter no ads, pdf to jpg unlimited free, pdf to jpg convert specific pages, pdf to image for mobile, pdf to image for instagram, pdf to image crop free, pdf to png crisp text, pdf to jpg converter for mac online, pdf to jpg convert all pages, pdf to image converter fast, pdf to image converter lightweight, convert pdf book to images, pdf diagrams to jpg free, extract pdf page as png, pdf to jpg converter with compression, convert pdf floor plans to jpg, pdf artwork to high-res images, pdf poster to jpg, pdf brochure to images, pdf to jpg for website upload, pdf to jpg text readable, pdf single page to jpg free",
        page_subtitle_key="Convert PDF pages to high-quality JPG images in seconds",
        header_text_key="PDF to JPG Converter",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_jpg_api",
        replace_regex=r"\.pdf$",
        replace_to=".zip",
        button_text_key="Convert PDF to JPG",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/pdf_to_jpg.html", context)


def jpg_to_pdf_page(request):
    """JPG to PDF conversion page."""
    context = _get_converter_context(
        page_title_key="JPG to PDF - Convertica",
        page_description_key="Convert JPG to PDF online free without compression. Merge multiple images into one PDF, combine photos to PDF, create PDF from images with high resolution. Perfect for documents, receipts, homework, and university submissions. No watermark, unlimited conversions.",
        page_keywords_key="JPG to PDF, image to PDF, jpg to pdf online free, png to pdf without compression, jpg to pdf merge multiple images, convert photos to pdf, jpg to pdf no watermark, image to pdf converter with margins, image to pdf high resolution, convert scanned photos to pdf, jpg to pdf for a4 format, multiple scans to pdf, png to pdf transparent background fix, jpg to pdf sharp quality, image to pdf fast conversion, combine images into one pdf, jpg to pdf converter for documents, png to pdf no ads, jpg to pdf converter unlimited, image to pdf for mobile upload, create pdf from images free, images to pdf without white borders, png to pdf maintain quality, jpg to pdf converter batch mode, convert drawings to pdf, convert screenshots to pdf, image to pdf converter for receipts, convert notes photos to pdf, image to pdf auto rotate, image to pdf correct orientation, png to pdf high-dpi, jpg to pdf file size small, large images to pdf converter, convert passport photo to pdf, combine photos to pdf online, jpg to pdf for homework, jpg to pdf for university submission, png to pdf color accurate, png to pdf flatten layers, image to pdf converter drag and drop, photos to pdf reorder pages, convert artwork scans to pdf",
        page_subtitle_key="Convert your JPG images to PDF format in seconds",
        header_text_key="JPG to PDF Converter",
        file_input_name="image_file",
        file_accept=".jpg,.jpeg",
        api_url_name="jpg_to_pdf_api",
        replace_regex=r"\.(jpg|jpeg|JPG|JPEG)$",
        replace_to=".pdf",
        button_text_key="Convert to PDF",
        select_file_message_key="Please select a JPG/JPEG image file.",
    )
    return render(request, "frontend/jpg_to_pdf.html", context)


def rotate_pdf_page(request):
    """Rotate PDF page."""
    context = _get_converter_context(
        page_title_key="Rotate PDF - Convertica",
        page_description_key="Rotate PDF pages online free by 90, 180, or 270 degrees. Fast PDF rotation tool with no watermark, batch rotation, and quality preservation. Perfect for scanned documents and misoriented pages. No registration required.",
        page_keywords_key="rotate PDF, PDF rotation, rotate pdf online free, rotate pdf pages 90 degrees, rotate pdf pages 180 degrees, rotate pdf pages 270 degrees, pdf rotation tool no watermark, rotate pdf fast online, rotate pdf batch, rotate multiple pdf pages, rotate pdf without losing quality, rotate scanned pdf, rotate pdf for printing, pdf rotation tool unlimited, rotate pdf no ads, rotate pdf safe tool, pdf rotation for mac online, pdf rotation for mobile, rotate pdf and save, pdf rotation maintain quality, rotate pdf pages clockwise, rotate pdf pages counterclockwise, fix pdf orientation, correct pdf page orientation, rotate pdf document, pdf rotation tool best 2025, rotate pdf high quality, rotate pdf for documents, rotate pdf for invoices, rotate pdf for reports, rotate pdf google drive safe, pdf rotation cloud tool, rotate pdf editor included, rotate pdf without errors, rotate pdf pages individually, rotate pdf all pages, rotate pdf specific pages, pdf rotation for students, free pdf rotation tool safe, rotate pdf without registration, rotate pdf one click",
        page_subtitle_key="Rotate your PDF pages in seconds",
        header_text_key="Rotate PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="rotate_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Rotate PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/rotate_pdf.html", context)


def add_page_numbers_page(request):
    """Add page numbers to PDF page."""
    context = _get_converter_context(
        page_title_key="Add Page Numbers to PDF - Convertica",
        page_description_key="Add page numbers to PDF online free with customizable position, font size, and format. Fast PDF page numbering tool with no watermark. Perfect for documents, reports, and academic papers. No registration required.",
        page_keywords_key="add page numbers PDF, PDF page numbers, add page numbers to pdf online free, number pdf pages, pdf page numbering tool, add page numbers pdf no watermark, pdf page numbers custom position, pdf page numbers font size, pdf page numbers format, add page numbers pdf fast, pdf page numbering unlimited, add page numbers pdf no ads, pdf page numbers for documents, pdf page numbers for reports, pdf page numbers for academic papers, add page numbers pdf batch, pdf page numbering maintain quality, add page numbers pdf safe tool, pdf page numbers top, pdf page numbers bottom, pdf page numbers center, pdf page numbers left, pdf page numbers right, add page numbers pdf for mac online, add page numbers pdf for mobile, pdf page numbering best 2025, add page numbers pdf high quality, pdf page numbers for students, free pdf page numbering tool safe, add page numbers pdf without registration, pdf page numbering one click, add page numbers pdf google drive safe, pdf page numbering cloud tool, add page numbers pdf editor included, pdf page numbers without errors, add page numbers pdf all pages, add page numbers pdf specific pages, pdf page numbering for invoices, pdf page numbers for legal documents",
        page_subtitle_key="Add page numbers to your PDF in seconds",
        header_text_key="Add Page Numbers",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="add_page_numbers_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Add Page Numbers",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/add_page_numbers.html", context)


def add_watermark_page(request):
    """Add watermark to PDF page."""
    context = _get_converter_context(
        page_title_key="Add Watermark to PDF - Convertica",
        page_description_key="Add watermark to PDF online free with text or image. Customize position, transparency, and size. Fast PDF watermarking tool with no watermark on tool itself. Perfect for document protection and branding. No registration required.",
        page_keywords_key="add watermark PDF, PDF watermark, add watermark to pdf online free, watermark pdf documents, pdf watermarking tool, add text watermark to pdf, add image watermark to pdf, pdf watermark custom position, pdf watermark transparency, pdf watermark size, add watermark pdf no watermark, pdf watermarking unlimited, add watermark pdf fast, pdf watermark for documents, pdf watermark for protection, pdf watermark for branding, add watermark pdf batch, pdf watermarking maintain quality, add watermark pdf safe tool, pdf watermark top, pdf watermark bottom, pdf watermark center, pdf watermark diagonal, add watermark pdf for mac online, add watermark pdf for mobile, pdf watermarking best 2025, add watermark pdf high quality, pdf watermark for students, free pdf watermarking tool safe, add watermark pdf without registration, pdf watermarking one click, add watermark pdf google drive safe, pdf watermarking cloud tool, add watermark pdf editor included, pdf watermark without errors, add watermark pdf all pages, add watermark pdf specific pages, pdf watermark for invoices, pdf watermark for legal documents, pdf watermark text, pdf watermark image, pdf watermark logo",
        page_subtitle_key="Add watermark to your PDF in seconds",
        header_text_key="Add Watermark",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="add_watermark_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Add Watermark",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/add_watermark.html", context)


def crop_pdf_page(request):
    """Crop PDF page."""
    context = _get_converter_context(
        page_title_key="Crop PDF - Convertica",
        page_description_key="Crop PDF pages online free with precise crop box coordinates. Fast PDF cropping tool with no watermark, visual editor, and quality preservation. Perfect for removing margins and unwanted content. No registration required.",
        page_keywords_key="crop PDF, PDF crop, crop pdf online free, crop pdf pages, pdf cropping tool, crop pdf with visual editor, crop pdf precise coordinates, crop pdf remove margins, crop pdf unwanted content, crop pdf fast online, pdf cropping no watermark, crop pdf unlimited, crop pdf batch, crop pdf without losing quality, crop pdf maintain quality, crop pdf safe tool, pdf cropping for mac online, pdf cropping for mobile, crop pdf and save, pdf cropping best 2025, crop pdf high quality, crop pdf for documents, crop pdf for printing, crop pdf for scanning, pdf cropping google drive safe, pdf cropping cloud tool, crop pdf editor included, pdf cropping without errors, crop pdf all pages, crop pdf specific pages, pdf cropping for students, free pdf cropping tool safe, crop pdf without registration, pdf cropping one click, crop pdf pages individually, crop pdf custom size, pdf cropping for invoices, pdf cropping for reports",
        page_subtitle_key="Crop your PDF pages in seconds",
        header_text_key="Crop PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="crop_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Crop PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/crop_pdf.html", context)


def merge_pdf_page(request):
    """Merge PDF page."""
    context = _get_converter_context(
        page_title_key="Merge PDF - Convertica",
        page_description_key="Merge PDF online free without watermark. Combine two PDFs into one, merge multiple PDF files fast, preserve bookmarks and quality. Unlimited PDF merger with drag and drop. No registration required.",
        page_keywords_key="merge PDF, combine PDF, merge pdf online free, combine two pdfs into one, merge pdf without watermark, pdf merger unlimited, combine pdf pages in order, merge multiple pdf files fast, merge pdf and preserve bookmarks, merge pdf no quality loss, pdf merge no ads, join pdf files secure, merge pdf large files, merge pdf drag and drop, combine pdf forms, merge pdf thesis chapters, merge pdf scanned pages, merge pdf double sided documents, merge pdf and reorder pages, merge protected pdfs, combine pdf receipts, merge pdf into single long file, merge pdf business documents, combine pdf statements, merge pdf drawings, merge pdf invoices, combine pdf lecture notes, merge pdf with table of contents, merge pdf into booklet, combine pdf without duplicates, merge pdf and compress, batch merge pdf online",
        page_subtitle_key="Combine multiple PDF files into one document",
        header_text_key="Merge PDF",
        file_input_name="pdf_files",
        file_accept=".pdf",
        api_url_name="merge_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Merge PDFs",
        select_file_message_key="Please select PDF files to merge.",
    )
    return render(request, "frontend/merge_pdf.html", context)


def split_pdf_page(request):
    """Split PDF page."""
    context = _get_converter_context(
        page_title_key="Split PDF - Convertica",
        page_description_key="Split PDF online free by pages, ranges, or bookmarks. Extract specific pages from PDF, remove pages, divide PDF into multiple files. Fast PDF splitter with no watermark. No registration required.",
        page_keywords_key="split PDF, divide PDF, split pdf online free, split pdf by pages, separate pdf into pages, pdf splitter no watermark, extract pages from pdf free, split pdf without losing quality, pdf splitter unlimited, extract specific pages pdf, split pdf by range online, split pdf every page, divide pdf into multiple files, pdf splitter with reorder, remove page from pdf online, delete pages from pdf free, split large pdf quickly, split pdf fast tool, extract pdf chapters, extract pdf table only, extract pdf images only, split pdf scanned file, extract odd pages pdf, extract even pages pdf, split pdf no ads, split pdf safe tool, separate pdf forms, pdf splitter for mac online, pdf splitter for mobile, extract pdf page to new file, pdf divider high quality, cut pdf into parts, remove front page pdf, remove blank pages pdf, split pdf school document, extract thesis pages pdf, extract invoice pages pdf, extract pdf long report, extract pdf cover page, pdf split maintain orientation, pdf split keep metadata, split pdf by bookmarks, pdf split by file size, split pdf for printing, extract pdf appendix, extract pdf annex, extract pdf diagrams, extract confidential pages pdf, split pdf interview transcript, cut pdf into equal parts, split scanned pdf pages",
        page_subtitle_key="Split your PDF into multiple files",
        header_text_key="Split PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="split_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".zip",
        button_text_key="Split PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/split_pdf.html", context)


def remove_pages_page(request):
    """Remove pages from PDF page."""
    context = _get_converter_context(
        page_title_key="Remove Pages from PDF - Convertica",
        page_description_key="Remove pages from PDF online free. Delete unwanted pages quickly and easily with no watermark. Fast PDF page removal tool. Perfect for cleaning up documents. No registration required.",
        page_keywords_key="remove PDF pages, delete PDF pages, remove pages from pdf online free, delete pdf pages, pdf page remover, remove pdf pages no watermark, delete pdf pages fast, remove pdf pages unlimited, remove pdf pages batch, remove pdf pages without losing quality, remove pdf pages maintain quality, remove pdf pages safe tool, pdf page removal for mac online, pdf page removal for mobile, remove pdf pages best 2025, remove pdf pages high quality, remove pdf pages for documents, remove pdf pages for reports, pdf page removal google drive safe, pdf page removal cloud tool, remove pdf pages editor included, pdf page removal without errors, remove pdf pages all pages, remove pdf pages specific pages, pdf page removal for students, free pdf page removal tool safe, remove pdf pages without registration, pdf page removal one click, remove pdf pages individually, remove pdf pages custom selection, pdf page removal for invoices, pdf page removal for legal documents",
        page_subtitle_key="Remove unwanted pages from your PDF",
        header_text_key="Remove Pages",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="remove_pages_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Remove Pages",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/remove_pages.html", context)


def extract_pages_page(request):
    """Extract pages from PDF page."""
    context = _get_converter_context(
        page_title_key="Extract Pages from PDF - Convertica",
        page_description_key="Extract pages from PDF online free. Select and extract specific pages to create a new PDF. Fast PDF page extraction tool with no watermark. Perfect for creating custom documents. No registration required.",
        page_keywords_key="extract PDF pages, PDF page extractor, extract pages from pdf online free, select pdf pages, pdf page extraction tool, extract pdf pages no watermark, extract pdf pages fast, extract pdf pages unlimited, extract pdf pages batch, extract pdf pages without losing quality, extract pdf pages maintain quality, extract pdf pages safe tool, pdf page extraction for mac online, pdf page extraction for mobile, extract pdf pages best 2025, extract pdf pages high quality, extract pdf pages for documents, extract pdf pages for reports, pdf page extraction google drive safe, pdf page extraction cloud tool, extract pdf pages editor included, pdf page extraction without errors, extract pdf pages all pages, extract pdf pages specific pages, extract pdf pages by range, extract pdf pages individually, pdf page extraction for students, free pdf page extraction tool safe, extract pdf pages without registration, pdf page extraction one click, extract pdf pages custom selection, pdf page extraction for invoices, pdf page extraction for legal documents",
        page_subtitle_key="Extract specific pages from your PDF",
        header_text_key="Extract Pages",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="extract_pages_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Extract Pages",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/extract_pages.html", context)


def organize_pdf_page(request):
    """Organize PDF page."""
    context = _get_converter_context(
        page_title_key="Organize PDF - Convertica",
        page_description_key="Organize PDF online free. Reorder pages, sort content, and manage your PDF files with drag and drop. Fast PDF organizer with no watermark. Perfect for organizing documents and reports. No registration required.",
        page_keywords_key="organize PDF, PDF organizer, organize pdf online free, reorder pdf pages, pdf page organizer, organize pdf documents, reorder pdf pages drag and drop, organize pdf pages sort, organize pdf content, organize pdf fast, pdf organizer no watermark, organize pdf unlimited, organize pdf batch, organize pdf without losing quality, organize pdf maintain quality, organize pdf safe tool, pdf organizer for mac online, pdf organizer for mobile, organize pdf and save, pdf organizer best 2025, organize pdf high quality, organize pdf for documents, organize pdf for reports, organize pdf for scanning, pdf organizer google drive safe, pdf organizer cloud tool, organize pdf editor included, pdf organizer without errors, organize pdf all pages, organize pdf specific pages, pdf organizer for students, free pdf organizer tool safe, organize pdf without registration, pdf organizer one click, organize pdf pages individually, organize pdf custom order, pdf organizer for invoices, pdf organizer for legal documents",
        page_subtitle_key="Organize and manage your PDF documents",
        header_text_key="Organize PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="organize_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Organize PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/organize_pdf.html", context)


def pdf_to_excel_page(request):
    """PDF to Excel conversion page."""
    context = _get_converter_context(
        page_title_key="PDF to Excel - Convertica",
        page_description_key="Convert PDF to Excel online free with accurate table extraction. Extract tables from PDF and convert to XLSX format. Perfect for invoices, reports, and data analysis. No registration required.",
        page_keywords_key="PDF to Excel, PDF to XLSX, convert PDF to Excel online free, pdf to excel without losing formatting, extract tables from pdf to excel, pdf table to excel converter, pdf to excel converter no email, pdf to excel fast online, convert pdf spreadsheet to excel, pdf to xlsx converter online free, pdf to excel converter unlimited, pdf to excel converter no sign up, convert pdf data to excel, pdf to excel export free, pdf to excel maintain formatting, pdf to excel high accuracy, convert pdf invoice to excel, pdf to excel batch converter, convert multiple pdf to excel online, pdf to excel no ads, pdf to excel no virus, pdf to excel converter small file, pdf to excel converter large file, pdf to excel converter clean layout, pdf to excel converter best 2025, pdf to excel converter high accuracy, pdf to excel converter for mac online, pdf to excel for linux online, pdf to excel converter for students, free pdf to excel tool safe, pdf to excel without registration, pdf to excel one click, extract pdf table to excel, pdf to excel keep formatting, pdf to excel high resolution, pdf to excel for invoices, pdf to excel for reports, pdf to excel google drive safe, pdf to excel cloud converter, pdf to excel export data only, pdf data to excel converter, pdf to excel editor included, pdf to excel converter without errors, convert pdf spreadsheet to excel, convert pdf data table to excel, pdf to excel table alignment maintained, pdf to excel for accounting, pdf to excel for business",
        page_subtitle_key="Extract tables from PDF and convert to Excel format",
        header_text_key="PDF to Excel Converter",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="pdf_to_excel_api",
        replace_regex=r"\.pdf$",
        replace_to=".xlsx",
        button_text_key="Convert PDF to Excel",
        select_file_message_key="Please select a PDF file with tables.",
    )
    return render(request, "frontend/converter_generic.html", context)


def compress_pdf_page(request):
    """Compress PDF page."""
    context = _get_converter_context(
        page_title_key="Compress PDF - Convertica",
        page_description_key="Compress PDF online free to reduce file size fast. PDF compressor with no watermark, compress PDF to under 1MB for email, reduce PDF file size without losing quality. Best PDF compression tool 2025.",
        page_keywords_key="compress PDF, PDF compressor, compress pdf online free, pdf compressor no watermark, reduce pdf file size fast, compress pdf for email, compress pdf to under 1mb, compress pdf to under 500kb, heavy pdf to small pdf, compress scanned pdf, pdf optimizer without quality loss, compress pdf images, shrink pdf without losing text clarity, pdf compressor easy, compress pdf batch, compress large pdf files, best pdf compression online, compress pdf for web upload, compress academic pdf, compress invoice pdf, compress color pdf, compress black and white pdf, compress pdf drawings, reduce pdf scan heavy images, compress pdf for mobile, pdf compression fast tool, compress pdf up to 90 percent, compress pdf animation included, compress graphics-heavy pdf, compress powerpoint exported pdf, compress ebook pdf, compress pdf keep quality, compress pdf ultra small, reduce pdf dpi free, convert and compress pdf, compress pdf from phone, compress pdf safe no upload, compress confidential pdf, compress pdf for printing, compress scanned docs pdf, reduce pdf file email limit, compress pdf reduce blur",
        page_subtitle_key="Reduce PDF file size without losing quality",
        header_text_key="Compress PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="compress_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Compress PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/compress_pdf.html", context)


def protect_pdf_page(request):
    """Protect PDF page."""
    context = _get_converter_context(
        page_title_key="Protect PDF with Password - Convertica",
        page_description_key="Protect PDF files with password encryption. Secure your PDF documents with strong password protection.",
        page_keywords_key="protect PDF, PDF password, encrypt PDF, PDF security, PDF protection, secure PDF",
        page_subtitle_key="Secure your PDF documents with password protection",
        header_text_key="Protect PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="protect_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Protect PDF",
        select_file_message_key="Please select a PDF file.",
    )
    return render(request, "frontend/protect_pdf.html", context)


def unlock_pdf_page(request):
    """Unlock PDF page."""
    context = _get_converter_context(
        page_title_key="Unlock PDF - Remove Password - Convertica",
        page_description_key="Unlock PDF online free. Remove password protection from PDF files with the correct password. Fast PDF unlock tool with no watermark. Perfect for accessing protected documents. No registration required.",
        page_keywords_key="unlock PDF, remove PDF password, unlock pdf online free, decrypt pdf, pdf unlock, pdf password remover, unlock pdf no watermark, unlock pdf fast, unlock pdf unlimited, unlock pdf batch, unlock pdf without losing quality, unlock pdf maintain quality, unlock pdf safe tool, pdf unlock for mac online, pdf unlock for mobile, unlock pdf best 2025, unlock pdf high quality, unlock pdf for documents, unlock pdf for reports, pdf unlock google drive safe, pdf unlock cloud tool, unlock pdf editor included, pdf unlock without errors, unlock pdf all pages, unlock pdf specific pages, pdf unlock for students, free pdf unlock tool safe, unlock pdf without registration, pdf unlock one click, unlock pdf with password, remove pdf password protection, decrypt pdf file, unlock encrypted pdf, pdf password removal, unlock protected pdf, remove pdf restrictions, unlock pdf for invoices, unlock pdf for legal documents",
        page_subtitle_key="Remove password protection from your PDF",
        header_text_key="Unlock PDF",
        file_input_name="pdf_file",
        file_accept=".pdf",
        api_url_name="unlock_pdf_api",
        replace_regex=r"\.pdf$",
        replace_to=".pdf",
        button_text_key="Unlock PDF",
        select_file_message_key="Please select a password-protected PDF file.",
    )
    return render(request, "frontend/unlock_pdf.html", context)


def all_tools_page(request):
    """All Tools page - shows all PDF tools organized by categories."""
    context = {
        "page_title": _("All PDF Tools - Convertica"),
        "page_description": _(
            "Browse all PDF tools: Convert, Edit, Organize, and Secure PDFs. Free online PDF tools for all your document needs."
        ),
        "page_keywords": _(
            "PDF tools, PDF converter, PDF editor, PDF organizer, PDF security, all PDF tools, online PDF tools, free PDF tools, free pdf tools online, pdf tools no registration, best pdf converter online, pdf editor online free, pdf tools for students, pdf tools for business, smallpdf alternative, ilovepdf alternative, adobe acrobat alternative, free pdf converter, pdf merger online, pdf splitter online, pdf compressor online, pdf rotator online, pdf watermark tool, high quality pdf converter, pdf converter no quality loss, pdf converter best quality, pdf converter for mac, pdf converter for windows, pdf converter for linux, pdf converter mobile, convert pdf to word for resume, merge pdf for thesis, compress pdf for email attachment, split pdf by chapters"
        ),
    }
    return render(request, "frontend/all_tools.html", context)


@cache_page(60 * 60 * 24 * 7)  # Cache for 7 days (604800 seconds)
def about_page(request):
    """About Us page."""
    context = {
        "page_title": _("About Us - Convertica"),
        "page_description": _(
            "Learn about Convertica - your trusted online PDF tools platform. We are committed to constant improvement and providing the best PDF conversion and editing experience."
        ),
        "page_keywords": _(
            "about Convertica, PDF tools company, online PDF converter, PDF services, document conversion"
        ),
    }
    return render(request, "frontend/about.html", context)


@cache_page(60 * 60 * 24 * 7)  # Cache for 7 days (604800 seconds)
def privacy_page(request):
    """Privacy Policy page."""
    context = {
        "page_title": _("Privacy Policy - Convertica"),
        "page_description": _(
            "Read Convertica's Privacy Policy. Learn how we protect your data and handle your files. Your privacy is our priority."
        ),
        "page_keywords": _(
            "privacy policy, data protection, file security, privacy, Convertica privacy"
        ),
    }
    return render(request, "frontend/privacy.html", context)


@cache_page(60 * 60 * 24 * 7)  # Cache for 7 days (604800 seconds)
def terms_page(request):
    """Terms of Service page."""
    context = {
        "page_title": _("Terms of Service - Convertica"),
        "page_description": _(
            "Read Convertica's Terms of Service. Understand the terms and conditions for using our PDF tools and services."
        ),
        "page_keywords": _(
            "terms of service, terms and conditions, user agreement, Convertica terms"
        ),
    }
    return render(request, "frontend/terms.html", context)


def contact_page(request):
    """Contact page with form handling."""
    import logging

    from django.conf import settings
    from django.contrib import messages
    from django.shortcuts import redirect

    from .forms import ContactForm

    logger = logging.getLogger(__name__)

    # If form was successfully submitted, show success message
    if request.method == "GET" and "sent" in request.GET:
        messages.success(
            request,
            _(
                "Thank you! Your message has been sent successfully. We'll get back to you as soon as possible, usually within 24-48 hours."
            ),
        )

    form = ContactForm()
    message_sent = False

    if request.method == "POST":
        form = ContactForm(request.POST)

        # Verify Turnstile before form validation
        from utils_site.src.api.spam_protection import verify_turnstile

        turnstile_token = request.POST.get("turnstile_token", "") or request.POST.get(
            "cf-turnstile-response", ""
        )

        # Get client IP
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
            return render(
                request,
                "frontend/contact.html",
                {
                    "page_title": _("Contact Us - Convertica"),
                    "page_description": _(
                        "Contact Convertica for support, questions, or feedback. We're here to help with all your PDF tool needs."
                    ),
                    "page_keywords": _(
                        "contact Convertica, support, customer service, help, feedback"
                    ),
                    "form": form,
                    "message_sent": False,
                },
            )

        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # Get recipient email from settings or use default
            recipient_email = getattr(settings, "CONTACT_EMAIL", "info@convertica.net")
            from_email = getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                f"noreply@{request.get_host()}",
            )
            user_ip = request.META.get("REMOTE_ADDR", "Unknown")

            # Prepare email content
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

            # Send email asynchronously via Celery to avoid blocking
            # This prevents the form from "hanging" if SMTP is slow/blocked
            from src.tasks.email import send_contact_form_email

            send_contact_form_email.delay(
                subject=email_subject,
                message=email_body,
                from_email=from_email,
                recipient_email=recipient_email,
                user_email=email,
                user_ip=user_ip,
            )

            # Log submission (email will be sent in background)
            logger.info(
                "Contact form submitted from %s (IP: %s) - email queued",
                email,
                user_ip,
            )

            # Redirect immediately - don't wait for email to be sent
            return redirect(f"{request.path}?sent=1")
        else:
            # Form validation errors
            messages.error(
                request,
                _("Please correct the errors in the form below."),
            )

    context = {
        "page_title": _("Contact Us - Convertica"),
        "page_description": _(
            "Contact Convertica for support, questions, or feedback. We're here to help with all your PDF tool needs."
        ),
        "page_keywords": _(
            "contact Convertica, support, customer service, help, feedback"
        ),
        "form": form,
        "message_sent": message_sent,
    }
    return render(request, "frontend/contact.html", context)


@cache_page(60 * 60 * 24)  # Cache for 24 hours (86400 seconds)
def faq_page(request):
    """FAQ page."""
    context = {
        "page_title": _("Frequently Asked Questions (FAQ) - Convertica"),
        "page_description": _(
            "Find answers to frequently asked questions about Convertica PDF tools. Learn how to convert, edit, and organize PDF files online for free."
        ),
        "page_keywords": _(
            "FAQ, frequently asked questions, PDF converter help, PDF tools FAQ, how to convert PDF, PDF questions, convert pdf to word online free, pdf to word without losing formatting, compress pdf online free, merge pdf online free, split pdf online free, pdf to jpg online free, jpg to pdf online free, pdf to excel online free, word to pdf online free, rotate pdf online free, add watermark to pdf online free, crop pdf online free, protect pdf online free, unlock pdf online free, pdf converter no email, pdf converter no registration, pdf converter unlimited, pdf converter no watermark, pdf converter fast, pdf converter safe, pdf converter free, pdf tools help, pdf conversion questions, pdf editing questions, pdf organization questions, pdf security questions"
        ),
        # FAQ structured data translations
        "faq_q1": _("How do I convert PDF to Word?"),
        "faq_a1": _(
            "To convert PDF to Word, simply upload your PDF file using the upload button or drag and drop it into the upload zone. Click the convert button and wait for the conversion to complete. Download your converted Word document using the download button. The conversion is free and requires no registration."
        ),
        "faq_q2": _("Is Convertica free to use?"),
        "faq_a2": _(
            "Yes, Convertica is completely free to use. All PDF conversion, editing, and organization tools are available at no cost. There are no hidden fees, no registration required, and no file size limits on the free plan."
        ),
        "faq_q3": _("What file formats does Convertica support?"),
        "faq_a3": _(
            "Convertica supports PDF, Word (DOC, DOCX), JPG/JPEG, and Excel formats. You can convert between these formats, edit PDFs, organize pages, and protect your documents with passwords."
        ),
        "faq_q4": _("How do I merge multiple PDF files?"),
        "faq_a4": _(
            "To merge PDF files, go to the Merge PDF page, select multiple PDF files, arrange them in the desired order, and click merge. All selected files will be combined into a single PDF document."
        ),
        "faq_q5": _("Is my data secure?"),
        "faq_a5": _(
            "Yes, your data is secure. All files are processed securely and automatically deleted immediately after conversion. We do not store your files, and your privacy is our top priority. You can also protect your PDFs with password encryption."
        ),
    }
    return render(request, "frontend/faq.html", context)


@require_http_methods(["GET"])
def sitemap_xml(request):
    """Generate sitemap.xml for SEO with multilingual support."""
    from django.conf import settings
    from django.core.cache import cache
    from django.utils.translation import activate, get_language
    from src.blog.models import Article

    # Cache sitemap for 24 hours
    cache_key = "sitemap_xml"
    cached_sitemap = cache.get(cache_key)
    if cached_sitemap:
        return HttpResponse(
            cached_sitemap, content_type="application/xml; charset=utf-8"
        )

    # Determine scheme: prefer X-Forwarded-Proto (from Nginx), fallback to request.scheme
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
    # Force HTTPS in production (if not DEBUG)
    if not getattr(settings, "DEBUG", False) and scheme == "http":
        scheme = "https"

    base_url = f"{scheme}://{request.get_host()}"
    current_date = datetime.now().strftime("%Y-%m-%d")
    languages = getattr(settings, "LANGUAGES", [("en", "English")])
    default_language = settings.LANGUAGE_CODE
    old_lang = get_language()

    # List of all important pages (without language prefix)
    pages = [
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

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'

    # Add static pages with all language versions
    for page in pages:
        page_url = page["url"]

        # Generate URL for each language
        for lang_code, _ in languages:
            # Django i18n_patterns adds prefix for ALL languages, including default
            # Build URL with language prefix for all languages
            if page_url == "":
                url = f"{base_url}/{lang_code}/"
            else:
                url = f"{base_url}/{lang_code}/{page_url}"

            sitemap += "  <url>\n"
            sitemap += f"    <loc>{url}</loc>\n"
            sitemap += f"    <lastmod>{current_date}</lastmod>\n"
            sitemap += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
            sitemap += f'    <priority>{page["priority"]}</priority>\n'

            # Add hreflang alternatives
            # Django i18n_patterns adds prefix for ALL languages, including default
            for alt_lang_code, _ in languages:
                if page_url == "":
                    alt_url = f"{base_url}/{alt_lang_code}/"
                else:
                    alt_url = f"{base_url}/{alt_lang_code}/{page_url}"

                sitemap += f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" href="{alt_url}"/>\n'

            # Add x-default pointing to default language version (with prefix)
            if page_url == "":
                default_url = f"{base_url}/{default_language}/"
            else:
                default_url = f"{base_url}/{default_language}/{page_url}"
            sitemap += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_url}"/>\n'

            sitemap += "  </url>\n"

    # Add blog articles with all language versions
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

        # Generate URL for each language
        for lang_code, _ in languages:
            activate(lang_code)
            try:
                article_url = article.get_absolute_url()
                # Ensure proper encoding
                if isinstance(article_url, bytes):
                    article_url = article_url.decode("utf-8")
            except Exception:
                # Fallback: construct URL manually
                # Django i18n_patterns adds prefix for ALL languages, including default
                article_url = f"/{lang_code}/blog/{article.slug}/"

            full_url = f"{base_url}{article_url}"

            sitemap += "  <url>\n"
            sitemap += f"    <loc>{full_url}</loc>\n"
            sitemap += f"    <lastmod>{lastmod}</lastmod>\n"
            sitemap += "    <changefreq>monthly</changefreq>\n"
            sitemap += "    <priority>0.7</priority>\n"

            # Add hreflang alternatives for article
            for alt_lang_code, _ in languages:
                activate(alt_lang_code)
                try:
                    alt_article_url = article.get_absolute_url()
                    if isinstance(alt_article_url, bytes):
                        alt_article_url = alt_article_url.decode("utf-8")
                except Exception:
                    # All languages have prefix, including default
                    alt_article_url = f"/{alt_lang_code}/blog/{article.slug}/"

                alt_full_url = f"{base_url}{alt_article_url}"
                sitemap += f'    <xhtml:link rel="alternate" hreflang="{alt_lang_code}" href="{alt_full_url}"/>\n'

            # Add x-default for article
            activate(default_language)
            try:
                default_article_url = article.get_absolute_url()
                if isinstance(default_article_url, bytes):
                    default_article_url = default_article_url.decode("utf-8")
            except Exception:
                # Default language also has prefix
                default_article_url = f"/{default_language}/blog/{article.slug}/"

            default_full_url = f"{base_url}{default_article_url}"
            sitemap += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_full_url}"/>\n'

            sitemap += "  </url>\n"

    # Restore original language
    activate(old_lang)

    sitemap += "</urlset>"

    # Cache for 24 hours
    cache.set(cache_key, sitemap, 86400)

    # Ensure proper encoding for XML response
    response = HttpResponse(sitemap, content_type="application/xml; charset=utf-8")
    response["Content-Type"] = "application/xml; charset=utf-8"
    return response
