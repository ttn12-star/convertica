# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import WordToPDFSerializer
from .decorators import word_to_pdf_docs
from .utils import convert_word_to_pdf
from ...base_views import BaseConversionAPIView


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

    @word_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Perform Word to PDF conversion."""
        docx_path, pdf_path = convert_word_to_pdf(
            uploaded_file,
            suffix="_convertica"
        )
        return docx_path, pdf_path
