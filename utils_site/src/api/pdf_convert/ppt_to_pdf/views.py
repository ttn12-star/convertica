"""
PowerPoint to PDF conversion API views.

Converts PPT/PPTX files to PDF using LibreOffice headless mode.
Supports both single file and batch processing for premium users.
"""

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

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

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        """Convert PowerPoint to PDF."""
        ppt_path, output_path = convert_ppt_to_pdf(uploaded_file, suffix="_convertica")
        return ppt_path, output_path

    def validate_file_additional(
        self, uploaded_file, context, validated_data
    ) -> Response | None:
        """Verify the PPT/PPTX magic bytes on the single-file (sync) path.

        Was a dead `validate_file()` override BaseConversionAPIView never calls,
        so the magic-byte check ran only on the batch path — see the twin fix in
        excel_to_pdf/views.py.
        """
        is_valid, error = validate_ppt_file(uploaded_file)
        if not is_valid:
            return Response(
                {"error": error or "Invalid PowerPoint file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None
