# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import RemovePagesSerializer
from .decorators import remove_pages_docs
from .utils import remove_pages
from ...base_views import BaseConversionAPIView


class RemovePagesAPIView(BaseConversionAPIView):
    """Handle remove pages from PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "REMOVE_PAGES"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return RemovePagesSerializer

    def get_docs_decorator(self):
        return remove_pages_docs

    @remove_pages_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Remove pages from PDF."""
        pages = kwargs.get('pages', '')
        pdf_path, output_path = remove_pages(
            uploaded_file,
            pages=pages,
            suffix="_convertica"
        )
        return pdf_path, output_path

