# views.py

import logging

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from src.tasks.pdf_conversion import convert_pdf_to_word_task

from ...base_views import BaseConversionAPIView
from .decorators import pdf_to_word_docs
from .serializers import PDFToWordSerializer
from .utils import convert_pdf_to_docx

logger = logging.getLogger(__name__)


class PDFToWordAPIView(BaseConversionAPIView):
    """Handle PDF → DOCX conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_word"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = (
        True  # Enforce server-side limits (free: 50 pages; premium: higher)
    )

    def get_serializer_class(self):
        return PDFToWordSerializer

    def get_docs_decorator(self):
        return pdf_to_word_docs

    def get_celery_task(self):
        """Get the Celery task function to execute."""
        return convert_pdf_to_word_task

    @pdf_to_word_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform PDF to DOCX conversion."""
        ocr_enabled = context.get("ocr_enabled", False)

        # Attach request to uploaded_file for language detection
        uploaded_file._request = self.request

        pdf_path, docx_path = async_to_sync(convert_pdf_to_docx)(
            uploaded_file,
            suffix="_convertica",
            ocr_enabled=ocr_enabled,
        )
        return pdf_path, docx_path
