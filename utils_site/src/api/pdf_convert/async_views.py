"""
Async versions of heavy PDF conversion views.

These views handle file uploads and immediately return a task_id
for async processing via Celery, avoiding Cloudflare timeouts.
"""

from django.conf import settings
from src.tasks.pdf_conversion import generic_conversion_task

from ..async_views import AsyncConversionAPIView
from .pdf_to_excel.serializers import PDFToExcelSerializer
from .pdf_to_word.serializers import PDFToWordSerializer
from .word_to_pdf.serializers import WordToPDFSerializer


class PDFToWordAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to Word conversion.

    Returns task_id immediately for progress polling.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_word"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False  # Client-side validation

    def get_serializer_class(self):
        return PDFToWordSerializer

    def get_celery_task(self):
        return generic_conversion_task


class PDFToExcelAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to Excel conversion.

    Returns task_id immediately for progress polling.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_excel"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False  # Client-side validation

    def get_serializer_class(self):
        return PDFToExcelSerializer

    def get_celery_task(self):
        return generic_conversion_task

    def get_task_kwargs(self, validated_data: dict) -> dict:
        """Pass pages parameter if provided."""
        return {"pages": validated_data.get("pages", "all")}


class WordToPDFAsyncAPIView(AsyncConversionAPIView):
    """Async Word to PDF conversion.

    Returns task_id immediately for progress polling.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".docx", ".doc"}
    CONVERSION_TYPE = "word_to_pdf"
    FILE_FIELD_NAME = "word_file"
    VALIDATE_PDF_PAGES = False  # Not a PDF input

    def get_serializer_class(self):
        return WordToPDFSerializer

    def get_celery_task(self):
        return generic_conversion_task
