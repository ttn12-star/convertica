from django.urls import path

from .pdf_to_word.views import PDFToWordAPIView
from .word_to_pdf.views import WordToPDFAPIView

urlpatterns = [
    path('pdf-to-word/', PDFToWordAPIView.as_view(), name='pdf_to_word_api'),
    path('word-to-pdf/', WordToPDFAPIView.as_view(), name='word_to_pdf_api'),
]
