"""
Excel to PDF conversion API views.

Converts XLS/XLSX files to PDF using LibreOffice headless mode.
Supports both single file and batch processing for premium users.
"""

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import excel_to_pdf_docs
from .serializers import ExcelToPDFSerializer
from .utils import convert_excel_to_pdf, validate_excel_file


class ExcelToPDFAPIView(BaseConversionAPIView):
    """Handle Excel → PDF conversion requests."""

    MAX_UPLOAD_SIZE = (
        50 * 1024 * 1024
    )  # 50 MB default, will be overridden by get_max_file_size()
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.ms-excel",  # .xls
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".xls", ".xlsx"}
    CONVERSION_TYPE = "excel_to_pdf"
    FILE_FIELD_NAME = "excel_file"
    VALIDATE_PDF_PAGES = False  # Not applicable for Excel files

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return ExcelToPDFSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return excel_to_pdf_docs

    @excel_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        """Convert Excel to PDF."""
        excel_path, output_path = convert_excel_to_pdf(
            uploaded_file,
            suffix="_convertica",
            orientation=kwargs.get("orientation", "auto"),
            fit_mode=kwargs.get("fit_mode", "fit_width"),
        )
        return excel_path, output_path

    def validate_file_additional(
        self, uploaded_file, context, validated_data
    ) -> Response | None:
        """Verify the XLS/XLSX magic bytes on the single-file (sync) path.

        This used to live in a `validate_file()` override that BaseConversionAPIView
        never calls (its `super().validate_file()` would even AttributeError), so
        the magic-byte check ran ONLY on the batch path — a file with an .xlsx
        name and octet-stream content reached LibreOffice/unoserver unvalidated,
        defeating the CVE mitigation validate_excel_file exists for.
        """
        is_valid, error = validate_excel_file(uploaded_file)
        if not is_valid:
            return Response(
                {"error": error or "Invalid Excel file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None
