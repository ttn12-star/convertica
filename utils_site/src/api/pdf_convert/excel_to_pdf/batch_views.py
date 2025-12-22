"""
Batch Excel to PDF conversion API views.

Supports processing up to 20 Excel files simultaneously for premium users.
Uses async processing for better performance with multiple files.
"""

from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import excel_to_pdf_docs
from .serializers import ExcelToPDFBatchSerializer
from .utils import convert_excel_to_pdf, validate_excel_file


class ExcelToPDFBatchAPIView(BaseConversionAPIView):
    """Handle batch Excel → PDF conversion requests."""

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.ms-excel",  # .xls
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".xls", ".xlsx"}
    CONVERSION_TYPE = "excel_to_pdf_batch"
    FILE_FIELD_NAME = "excel_files"
    VALIDATE_PDF_PAGES = False  # Not applicable for Excel files

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return ExcelToPDFBatchSerializer

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
            uploaded_file, suffix="_convertica"
        )
        return excel_path, output_path

    def validate_file(self, uploaded_file, request) -> tuple[bool, str | None]:
        """Validate Excel file before conversion."""
        # First run base validation (size, extension, etc.)
        is_valid, error = super().validate_file(uploaded_file, request)
        if not is_valid:
            return False, error

        # Then run Excel-specific validation
        return validate_excel_file(uploaded_file)
