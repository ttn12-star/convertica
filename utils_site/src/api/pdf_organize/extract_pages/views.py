# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import ExtractPagesSerializer
from .decorators import extract_pages_docs
from .utils import extract_pages
from ...base_views import BaseConversionAPIView


class ExtractPagesAPIView(BaseConversionAPIView):
    """Handle extract pages from PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "EXTRACT_PAGES"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return ExtractPagesSerializer

    def get_docs_decorator(self):
        return extract_pages_docs

    @extract_pages_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Extract pages from PDF."""
        pages = kwargs.get('pages', '')
        pdf_path, output_path = extract_pages(
            uploaded_file,
            pages=pages,
            suffix="_convertica"
        )
        return pdf_path, output_path

