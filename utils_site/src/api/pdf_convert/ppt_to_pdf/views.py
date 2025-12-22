"""
PowerPoint to PDF conversion API views.

Converts PPT/PPTX files to PDF using LibreOffice headless mode.
Supports both single file and batch processing for premium users.
"""

from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import ppt_to_pdf_docs
from .serializers import PowerPointToPDFSerializer
from .utils import convert_ppt_to_pdf, validate_ppt_file


class PowerPointToPDFAPIView(BaseConversionAPIView):
    """Handle PowerPoint → PDF conversion requests."""

    MAX_UPLOAD_SIZE = (
        50 * 1024 * 1024
    )  # 50 MB default, will be overridden by get_max_file_size()
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.ms-powerpoint",  # .ppt
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".ppt", ".pptx"}
    CONVERSION_TYPE = "ppt_to_pdf"
    FILE_FIELD_NAME = "ppt_file"
    VALIDATE_PDF_PAGES = False  # Not applicable for PowerPoint files

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return PowerPointToPDFSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return ppt_to_pdf_docs

    @ppt_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, uploaded_file, **kwargs) -> tuple[str, str]:
        """Convert PowerPoint to PDF."""
        ppt_path, output_path = convert_ppt_to_pdf(uploaded_file, suffix="_convertica")
        return ppt_path, output_path

    def validate_file(self, uploaded_file, request) -> tuple[bool, str | None]:
        """Validate PowerPoint file before conversion."""
        # First run base validation (size, extension, etc.)
        is_valid, error = super().validate_file(uploaded_file, request)
        if not is_valid:
            return False, error

        # Then run PowerPoint-specific validation
        return validate_ppt_file(uploaded_file)
