"""
Async versions of heavy PDF organization views.

These views handle file uploads and immediately return a task_id
for async processing via Celery, avoiding Cloudflare timeouts.
"""

from django.conf import settings
from src.tasks.pdf_conversion import generic_conversion_task

from ..async_views import AsyncConversionAPIView
from .compress_pdf.serializers import CompressPDFSerializer


class CompressPDFAsyncAPIView(AsyncConversionAPIView):
    """Async PDF compression.

    Returns task_id immediately for progress polling.
    Useful for large PDFs.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "compress_pdf"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False  # No page limit for compression

    def get_serializer_class(self):
        return CompressPDFSerializer

    def get_celery_task(self):
        return generic_conversion_task

    def get_task_kwargs(self, validated_data: dict) -> dict:
        """Pass compression level parameter."""
        return {
            "compression_level": validated_data.get("compression_level", "medium"),
        }
