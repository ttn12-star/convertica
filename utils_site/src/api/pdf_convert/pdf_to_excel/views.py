# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import pdf_to_excel_docs
from .serializers import PDFToExcelSerializer
from .utils import convert_pdf_to_excel


class PDFToExcelAPIView(BaseConversionAPIView):
    """Handle PDF to Excel conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_EXCEL"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return PDFToExcelSerializer

    def get_docs_decorator(self):
        return pdf_to_excel_docs

    @pdf_to_excel_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Convert PDF to Excel."""
        pages = kwargs.get("pages", "all")
        pdf_path, output_path = convert_pdf_to_excel(
            uploaded_file, pages=pages, suffix="_convertica"
        )
        return pdf_path, output_path

    def get_output_content_type(self, output_path: str = None) -> str:
        """Return Excel content type."""
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
