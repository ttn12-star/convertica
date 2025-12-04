# utils_site/src/frontend/views.py

from django.shortcuts import render
from django.urls import reverse

def index_page(request):
    return render(request, 'frontend/index.html')

def pdf_to_word_page(request):
    context = {
        'page_title': 'PDF to Word - Convertica',
        'page_description': 'Upload PDF files and download Word documents instantly. Free PDF to DOCX converter online.',
        'header_text': 'PDF → Word Converter',
        'file_input_name': 'pdf_file',
        'file_accept': '.pdf',
        'button_class': 'bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700',
        'button_text': 'Convert PDF to Word',
        'select_file_message': 'Please select a PDF file.',
        'api_url': reverse('pdf_to_word_api'),
        'replace_regex': r'\.pdf$',
        'replace_to': '.docx',
        'error_message': 'Conversion failed.',
    }
    return render(request, 'frontend/pdf_to_word.html', context)

def word_to_pdf_page(request):
    context = {
        'page_title': 'Word to PDF - Convertica',
        'page_description': 'Upload Word files and download PDF documents instantly. Convert DOC/DOCX to PDF online for free.',
        'header_text': 'Word → PDF Converter',
        'file_input_name': 'word_file',
        'file_accept': '.doc,.docx',
        'button_class': 'bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700',
        'button_text': 'Convert to PDF',
        'select_file_message': 'Please select a Word file.',
        'api_url': reverse('word_to_pdf_api'),
        'replace_regex': r'\.(docx?|DOCX?)$',
        'replace_to': '.pdf',
        'error_message': 'Conversion failed.',
    }
    return render(request, 'frontend/word_to_pdf.html', context)