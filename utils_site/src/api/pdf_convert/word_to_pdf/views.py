# views.py

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from src.tasks.pdf_conversion import convert_word_to_pdf_task

from ...base_views import BaseConversionAPIView
from .decorators import word_to_pdf_docs
from .serializers import WordToPDFSerializer


class WordToPDFAPIView(BaseConversionAPIView):
    """Handle Word (.doc/.docx) → PDF conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".doc", ".docx"}
    CONVERSION_TYPE = "WORD_TO_PDF"
    FILE_FIELD_NAME = "word_file"

    def get_serializer_class(self):
        return WordToPDFSerializer

    def get_docs_decorator(self):
        return word_to_pdf_docs

    def get_celery_task(self):
        """Get the Celery task function to execute."""
        return convert_word_to_pdf_task

    def get(self, request: HttpRequest):
        """Handle GET request - return method not allowed."""
        return Response(
            {"error": "GET method not allowed. Use POST to convert files."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @word_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return async_to_sync(self.post_async)(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform Word to PDF conversion."""
        from src.api.pdf_convert.word_to_pdf.utils import (
            convert_word_to_pdf as convert_word_to_pdf_sync,
        )

        docx_path, pdf_path = convert_word_to_pdf_sync(
            uploaded_file, suffix="_convertica"
        )
        return docx_path, pdf_path
