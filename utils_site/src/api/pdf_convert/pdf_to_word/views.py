# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import pdf_to_word_docs
from .serializers import PDFToWordSerializer
from .utils import convert_pdf_to_docx


class PDFToWordAPIView(BaseConversionAPIView):
    """Handle PDF → DOCX conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_WORD"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return PDFToWordSerializer

    def get_docs_decorator(self):
        return pdf_to_word_docs

    @pdf_to_word_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform PDF to DOCX conversion."""
        pdf_path, docx_path = convert_pdf_to_docx(uploaded_file, suffix="_convertica")
        return pdf_path, docx_path
