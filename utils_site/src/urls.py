from django.urls import path

from api.pdf_to_word.views import PDFToWordAPIView
from api.word_to_pdf.views import WordToPDFAPIView

urlpatterns = [
    path('pdf-to-word/', PDFToWordAPIView.as_view(), name='api_pdf_to_word'),
    path('word-to-pdf/', WordToPDFAPIView.as_view(), name='api_word_to_pdf'),
]
