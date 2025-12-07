# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import organize_pdf_docs
from .serializers import OrganizePDFSerializer
from .utils import organize_pdf


class OrganizePDFAPIView(BaseConversionAPIView):
    """Handle general PDF organization requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "ORGANIZE_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return OrganizePDFSerializer

    def get_docs_decorator(self):
        return organize_pdf_docs

    @organize_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> Tuple[str, str]:
        """Organize PDF."""
        operation = kwargs.get("operation", "reorder")
        page_order = kwargs.get("page_order")
        pdf_path, output_path = organize_pdf(
            uploaded_file,
            operation=operation,
            page_order=page_order,
            suffix="_convertica",
        )
        return pdf_path, output_path
