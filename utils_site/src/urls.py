from django.urls import path
from api.pdf_to_word.views import PDFToWordAPIView

urlpatterns = [
    path('pdf-to-word/', PDFToWordAPIView.as_view(), name='api_pdf_to_word'),
]
