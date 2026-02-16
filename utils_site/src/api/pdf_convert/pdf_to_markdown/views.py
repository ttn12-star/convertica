"""API view for PDF to Markdown conversion."""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .decorators import pdf_to_markdown_docs
from .serializers import PDFToMarkdownSerializer
from .utils import convert_pdf_to_markdown


def _premium_access_error(request: HttpRequest) -> Response:
    """Build premium-required API response."""
    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
    if not request.user.is_authenticated:
        if payments_enabled:
            message = "This converter is available for premium users. Please log in and upgrade."
        else:
            message = "This converter is currently unavailable."
    else:
        if payments_enabled:
            message = "This converter is available for premium users. Upgrade to Premium to continue."
        else:
            message = "This converter is currently unavailable."
    return Response({"error": message}, status=status.HTTP_403_FORBIDDEN)


class PDFToMarkdownAPIView(BaseConversionAPIView):
    """Handle PDF to Markdown conversion requests (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_MARKDOWN"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return PDFToMarkdownSerializer

    def get_docs_decorator(self):
        return pdf_to_markdown_docs

    @pdf_to_markdown_docs()
    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return convert_pdf_to_markdown(
            uploaded_file=uploaded_file,
            detect_headings=kwargs.get("detect_headings", True),
            preserve_tables=kwargs.get("preserve_tables", True),
            suffix="_convertica",
        )

    def get_output_content_type(self, output_path: str) -> str:
        return "text/markdown; charset=utf-8"
