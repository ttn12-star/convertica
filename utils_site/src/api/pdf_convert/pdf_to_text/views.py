"""API view for PDF to Text conversion."""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import pdf_to_text_docs
from .serializers import PDFToTextSerializer
from .utils import convert_pdf_to_text


class PDFToTextAPIView(BaseConversionAPIView):
    """Handle PDF to Text conversion requests (free, global daily quota)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_TEXT"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return PDFToTextSerializer

    def get_docs_decorator(self):
        return pdf_to_text_docs

    @pdf_to_text_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Extract text from PDF."""
        include_page_numbers = kwargs.get("include_page_numbers", False)
        preserve_layout = kwargs.get("preserve_layout", False)

        return convert_pdf_to_text(
            pdf_file=uploaded_file,
            include_page_numbers=include_page_numbers,
            preserve_layout=preserve_layout,
            suffix="_convertica",
        )

    def get_output_content_type(self, output_path: str) -> str:
        return "text/plain; charset=utf-8"
