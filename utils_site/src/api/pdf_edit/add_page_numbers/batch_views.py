"""
Batch PDF page numbers API views.

Supports processing up to 10 PDF files simultaneously for premium users.
All files get page numbers with the same parameters and returned as a ZIP archive.
"""

from django.http import HttpRequest
from src.api.rate_limit_utils import combined_rate_limit

from ...base_views import BaseConversionAPIView
from .batch_serializers import AddPageNumbersBatchSerializer
from .decorators import add_page_numbers_docs
from .utils import add_page_numbers


class AddPageNumbersBatchAPIView(BaseConversionAPIView):
    """Handle batch PDF page numbers requests."""

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "add_page_numbers_batch"
    FILE_FIELD_NAME = "pdf_files"
    VALIDATE_PDF_PAGES = False  # Client-side validation

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return AddPageNumbersBatchSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return add_page_numbers_docs

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @add_page_numbers_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        """Add page numbers to PDF with specified parameters."""
        position = kwargs.get("position", "bottom-center")
        font_size = int(kwargs.get("font_size", 12))
        color = kwargs.get("color", "#000000")
        format_type = kwargs.get("format", "number")
        start_number = int(kwargs.get("start_number", 1))
        pages = kwargs.get("pages", "all")

        input_path, output_path = add_page_numbers(
            uploaded_file=uploaded_file,
            position=position,
            font_size=font_size,
            color=color,
            format_type=format_type,
            start_number=start_number,
            pages=pages,
            suffix="_numbered",
        )

        return input_path, output_path
