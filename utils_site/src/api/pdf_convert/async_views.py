"""
Async versions of heavy PDF conversion views.

These views handle file uploads and immediately return a task_id
for async processing via Celery, avoiding Cloudflare timeouts.

Note: VALIDATE_PDF_PAGES = True enables early rejection of files
that are too large/complex to process on our limited server.
"""

from django.conf import settings
from src.tasks.pdf_conversion import generic_conversion_task

from ..async_views import AsyncConversionAPIView
from ..conversion_limits import MAX_FILE_SIZE_HEAVY, MAX_PDF_PAGES_HEAVY
from .pdf_to_excel.serializers import PDFToExcelSerializer
from .pdf_to_jpg.serializers import PDFToJPGSerializer
from .pdf_to_word.serializers import PDFToWordSerializer
from .word_to_pdf.serializers import WordToPDFSerializer


class PDFToWordAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to Word conversion.

    Returns task_id immediately for progress polling.
    Uses stricter limits due to memory-intensive processing.
    """

    MAX_UPLOAD_SIZE = MAX_FILE_SIZE_HEAVY  # 15 MB for heavy operations
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_word"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True  # Enable validation for early rejection
    MAX_PDF_PAGES = MAX_PDF_PAGES_HEAVY  # 50 pages for heavy operations

    def get_serializer_class(self):
        return PDFToWordSerializer

    def get_celery_task(self):
        return generic_conversion_task


class PDFToExcelAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to Excel conversion.

    Returns task_id immediately for progress polling.
    Uses stricter limits due to memory-intensive processing.
    """

    MAX_UPLOAD_SIZE = MAX_FILE_SIZE_HEAVY  # 15 MB for heavy operations
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_excel"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True  # Enable validation for early rejection
    MAX_PDF_PAGES = MAX_PDF_PAGES_HEAVY  # 50 pages for heavy operations

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
    Uses stricter size limit due to LibreOffice memory usage.
    """

    MAX_UPLOAD_SIZE = MAX_FILE_SIZE_HEAVY  # 15 MB for heavy operations
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".docx", ".doc"}
    CONVERSION_TYPE = "word_to_pdf"
    FILE_FIELD_NAME = "word_file"
    VALIDATE_PDF_PAGES = False  # Not a PDF input (but size is still checked)

    def get_serializer_class(self):
        return WordToPDFSerializer

    def get_celery_task(self):
        return generic_conversion_task


class PDFToJPGAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to JPG conversion.

    Returns task_id immediately for progress polling.
    Useful for large PDFs or high DPI settings.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 25 * 1024 * 1024)  # 25 MB
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_jpg"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True  # Enable validation
    MAX_PDF_PAGES = 50  # Standard limit for image extraction

    def get_serializer_class(self):
        return PDFToJPGSerializer

    def get_celery_task(self):
        return generic_conversion_task

    def get_task_kwargs(self, validated_data: dict) -> dict:
        """Pass pages and DPI parameters."""
        return {
            "pages": validated_data.get("pages", "all"),
            "dpi": validated_data.get("dpi", 300),
        }
