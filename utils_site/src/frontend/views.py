# utils_site/src/frontend/views.py

from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def index_page(request):
    """Home page view."""
    context = {
        'page_title': _('Convertica – Online PDF ↔ Word Converter'),
        'page_description': _('Fast, simple and secure online PDF to Word and Word to PDF converter. Convert documents instantly, no registration required.'),
        'page_keywords': _('PDF to Word, Word to PDF, PDF converter, DOCX converter, online converter, free converter, convert PDF, convert Word'),
    }
    return render(request, 'frontend/index.html', context)


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
    button_class: str = 'bg-blue-600 text-white hover:bg-blue-700',
) -> dict:
    """Helper function to generate converter page context.
    
    Args:
        page_title_key: Translation key for page title
        page_description_key: Translation key for page description
        page_keywords_key: Translation key for page keywords
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
    return {
        'page_title': _(page_title_key),
        'page_description': _(page_description_key),
        'page_keywords': _(page_keywords_key),
        'page_subtitle': _(page_subtitle_key),
        'header_text': _(header_text_key),
        'file_input_name': file_input_name,
        'file_accept': file_accept,
        'button_class': button_class,
        'button_text': _(button_text_key),
        'select_file_message': _(select_file_message_key),
        'api_url': reverse(api_url_name),
        'replace_regex': replace_regex,
        'replace_to': replace_to,
        'error_message': _('Conversion failed. Please try again.'),
    }


def pdf_to_word_page(request):
    """PDF to Word conversion page."""
    context = _get_converter_context(
        page_title_key='PDF to Word - Convertica',
        page_description_key='Upload PDF files and download Word documents instantly. Free PDF to DOCX converter online. No registration required.',
        page_keywords_key='PDF to Word, PDF to DOCX, convert PDF, PDF converter, Word converter, online PDF converter',
        page_subtitle_key='Convert your PDF documents to editable Word format in seconds',
        header_text_key='PDF to Word Converter',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='pdf_to_word_api',
        replace_regex=r'\.pdf$',
        replace_to='.docx',
        button_text_key='Convert PDF to Word',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/converter_generic.html', context)


def word_to_pdf_page(request):
    """Word to PDF conversion page."""
    context = _get_converter_context(
        page_title_key='Word to PDF - Convertica',
        page_description_key='Upload Word files and download PDF documents instantly. Convert DOC/DOCX to PDF online for free. No registration required.',
        page_keywords_key='Word to PDF, DOCX to PDF, DOC to PDF, convert Word, Word converter, PDF converter, online converter',
        page_subtitle_key='Convert your Word documents to PDF format in seconds',
        header_text_key='Word to PDF Converter',
        file_input_name='word_file',
        file_accept='.doc,.docx',
        api_url_name='word_to_pdf_api',
        replace_regex=r'\.(docx?|DOCX?)$',
        replace_to='.pdf',
        button_text_key='Convert to PDF',
        select_file_message_key='Please select a Word file.',
    )
    return render(request, 'frontend/converter_generic.html', context)


def pdf_to_jpg_page(request):
    """PDF to JPG conversion page."""
    context = _get_converter_context(
        page_title_key='PDF to JPG - Convertica',
        page_description_key='Convert PDF pages to JPG images instantly. Free PDF to image converter online. High quality conversion with customizable DPI.',
        page_keywords_key='PDF to JPG, PDF to image, convert PDF to JPG, PDF image converter, online PDF converter',
        page_subtitle_key='Convert PDF pages to high-quality JPG images in seconds',
        header_text_key='PDF to JPG Converter',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='pdf_to_jpg_api',
        replace_regex=r'\.pdf$',
        replace_to='.jpg',
        button_text_key='Convert PDF to JPG',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/converter_generic.html', context)


def jpg_to_pdf_page(request):
    """JPG to PDF conversion page."""
    context = _get_converter_context(
        page_title_key='JPG to PDF - Convertica',
        page_description_key='Convert JPG images to PDF documents instantly. Free image to PDF converter online. Multiple images supported.',
        page_keywords_key='JPG to PDF, image to PDF, convert JPG to PDF, image PDF converter, online converter',
        page_subtitle_key='Convert your JPG images to PDF format in seconds',
        header_text_key='JPG to PDF Converter',
        file_input_name='image_file',
        file_accept='.jpg,.jpeg',
        api_url_name='jpg_to_pdf_api',
        replace_regex=r'\.(jpg|jpeg|JPG|JPEG)$',
        replace_to='.pdf',
        button_text_key='Convert to PDF',
        select_file_message_key='Please select a JPG/JPEG image file.',
    )
    return render(request, 'frontend/converter_generic.html', context)


def rotate_pdf_page(request):
    """Rotate PDF page."""
    context = _get_converter_context(
        page_title_key='Rotate PDF - Convertica',
        page_description_key='Rotate PDF pages by 90, 180, or 270 degrees. Free online PDF rotation tool.',
        page_keywords_key='rotate PDF, PDF rotation, rotate PDF pages, PDF editor, online PDF tool',
        page_subtitle_key='Rotate your PDF pages in seconds',
        header_text_key='Rotate PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='rotate_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Rotate PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/rotate_pdf.html', context)


def add_page_numbers_page(request):
    """Add page numbers to PDF page."""
    context = _get_converter_context(
        page_title_key='Add Page Numbers to PDF - Convertica',
        page_description_key='Add page numbers to PDF documents. Customize position, font size, and format.',
        page_keywords_key='add page numbers PDF, PDF page numbers, number PDF pages, PDF editor',
        page_subtitle_key='Add page numbers to your PDF in seconds',
        header_text_key='Add Page Numbers',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='add_page_numbers_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Add Page Numbers',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/add_page_numbers.html', context)


def add_watermark_page(request):
    """Add watermark to PDF page."""
    context = _get_converter_context(
        page_title_key='Add Watermark to PDF - Convertica',
        page_description_key='Add text or image watermark to PDF documents. Protect your documents with custom watermarks.',
        page_keywords_key='add watermark PDF, PDF watermark, watermark PDF, PDF protection',
        page_subtitle_key='Add watermark to your PDF in seconds',
        header_text_key='Add Watermark',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='add_watermark_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Add Watermark',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/add_watermark.html', context)


def crop_pdf_page(request):
    """Crop PDF page."""
    context = _get_converter_context(
        page_title_key='Crop PDF - Convertica',
        page_description_key='Crop PDF pages by specifying crop box coordinates. Free online PDF cropping tool.',
        page_keywords_key='crop PDF, PDF crop, crop PDF pages, PDF editor, online PDF tool',
        page_subtitle_key='Crop your PDF pages in seconds',
        header_text_key='Crop PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='crop_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Crop PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/crop_pdf.html', context)


def merge_pdf_page(request):
    """Merge PDF page."""
    context = _get_converter_context(
        page_title_key='Merge PDF - Convertica',
        page_description_key='Merge multiple PDF files into one document. Combine PDFs online for free. Fast and secure.',
        page_keywords_key='merge PDF, combine PDF, join PDF, PDF merger, online PDF tool',
        page_subtitle_key='Combine multiple PDF files into one document',
        header_text_key='Merge PDF',
        file_input_name='pdf_files',
        file_accept='.pdf',
        api_url_name='merge_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Merge PDFs',
        select_file_message_key='Please select PDF files to merge.',
    )
    return render(request, 'frontend/merge_pdf.html', context)


def split_pdf_page(request):
    """Split PDF page."""
    context = _get_converter_context(
        page_title_key='Split PDF - Convertica',
        page_description_key='Split PDF into multiple files. Extract pages or divide PDF by pages, ranges, or every N pages.',
        page_keywords_key='split PDF, divide PDF, extract PDF pages, PDF splitter, online PDF tool',
        page_subtitle_key='Split your PDF into multiple files',
        header_text_key='Split PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='split_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.zip',
        button_text_key='Split PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/split_pdf.html', context)


def remove_pages_page(request):
    """Remove pages from PDF page."""
    context = _get_converter_context(
        page_title_key='Remove Pages from PDF - Convertica',
        page_description_key='Remove specific pages from PDF documents. Delete unwanted pages quickly and easily.',
        page_keywords_key='remove PDF pages, delete PDF pages, PDF page remover, online PDF tool',
        page_subtitle_key='Remove unwanted pages from your PDF',
        header_text_key='Remove Pages',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='remove_pages_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Remove Pages',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/remove_pages.html', context)


def extract_pages_page(request):
    """Extract pages from PDF page."""
    context = _get_converter_context(
        page_title_key='Extract Pages from PDF - Convertica',
        page_description_key='Extract specific pages from PDF documents. Create new PDF with selected pages only.',
        page_keywords_key='extract PDF pages, PDF page extractor, select PDF pages, online PDF tool',
        page_subtitle_key='Extract specific pages from your PDF',
        header_text_key='Extract Pages',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='extract_pages_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Extract Pages',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/extract_pages.html', context)


def organize_pdf_page(request):
    """Organize PDF page."""
    context = _get_converter_context(
        page_title_key='Organize PDF - Convertica',
        page_description_key='Organize PDF documents. Reorder pages, sort content, and manage your PDF files.',
        page_keywords_key='organize PDF, PDF organizer, reorder PDF pages, PDF management, online PDF tool',
        page_subtitle_key='Organize and manage your PDF documents',
        header_text_key='Organize PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='organize_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Organize PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/organize_pdf.html', context)


def pdf_to_excel_page(request):
    """PDF to Excel conversion page."""
    context = _get_converter_context(
        page_title_key='PDF to Excel - Convertica',
        page_description_key='Convert PDF tables to Excel spreadsheets. Extract tables from PDF and convert to XLSX format. Free online PDF to Excel converter.',
        page_keywords_key='PDF to Excel, PDF to XLSX, convert PDF tables, PDF table extractor, Excel converter, online PDF converter',
        page_subtitle_key='Extract tables from PDF and convert to Excel format',
        header_text_key='PDF to Excel Converter',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='pdf_to_excel_api',
        replace_regex=r'\.pdf$',
        replace_to='.xlsx',
        button_text_key='Convert PDF to Excel',
        select_file_message_key='Please select a PDF file with tables.',
    )
    return render(request, 'frontend/converter_generic.html', context)


def compress_pdf_page(request):
    """Compress PDF page."""
    context = _get_converter_context(
        page_title_key='Compress PDF - Convertica',
        page_description_key='Compress PDF files to reduce file size. Free online PDF compression tool. Reduce PDF size for email and upload.',
        page_keywords_key='compress PDF, PDF compression, reduce PDF size, PDF optimizer, online PDF tool',
        page_subtitle_key='Reduce PDF file size without losing quality',
        header_text_key='Compress PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='compress_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Compress PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/compress_pdf.html', context)


def protect_pdf_page(request):
    """Protect PDF page."""
    context = _get_converter_context(
        page_title_key='Protect PDF with Password - Convertica',
        page_description_key='Protect PDF files with password encryption. Secure your PDF documents with strong password protection.',
        page_keywords_key='protect PDF, PDF password, encrypt PDF, PDF security, PDF protection, secure PDF',
        page_subtitle_key='Secure your PDF documents with password protection',
        header_text_key='Protect PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='protect_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Protect PDF',
        select_file_message_key='Please select a PDF file.',
    )
    return render(request, 'frontend/protect_pdf.html', context)


def unlock_pdf_page(request):
    """Unlock PDF page."""
    context = _get_converter_context(
        page_title_key='Unlock PDF - Remove Password - Convertica',
        page_description_key='Remove password protection from PDF files. Unlock encrypted PDF documents with the correct password.',
        page_keywords_key='unlock PDF, remove PDF password, decrypt PDF, PDF unlock, PDF password remover',
        page_subtitle_key='Remove password protection from your PDF',
        header_text_key='Unlock PDF',
        file_input_name='pdf_file',
        file_accept='.pdf',
        api_url_name='unlock_pdf_api',
        replace_regex=r'\.pdf$',
        replace_to='.pdf',
        button_text_key='Unlock PDF',
        select_file_message_key='Please select a password-protected PDF file.',
    )
    return render(request, 'frontend/unlock_pdf.html', context)


def all_tools_page(request):
    """All Tools page - shows all PDF tools organized by categories."""
    context = {
        'page_title': _('All PDF Tools - Convertica'),
        'page_description': _('Browse all PDF tools: Convert, Edit, Organize, and Secure PDFs. Free online PDF tools for all your document needs.'),
        'page_keywords': _('PDF tools, PDF converter, PDF editor, PDF organizer, PDF security, all PDF tools, online PDF tools, free PDF tools'),
    }
    return render(request, 'frontend/all_tools.html', context)
