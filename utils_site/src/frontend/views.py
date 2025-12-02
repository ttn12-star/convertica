# utils_site/src/frontend/views.py

from django.shortcuts import render

def index_page(request):
    return render(request, 'frontend/index.html')

def pdf_to_word_page(request):
    return render(request, 'frontend/pdf_to_word.html')

def word_to_pdf_page(request):
    return render(request, 'frontend/word_to_pdf.html')
