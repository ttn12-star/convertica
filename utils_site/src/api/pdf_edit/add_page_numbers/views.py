# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import add_page_numbers_docs
from .serializers import AddPageNumbersSerializer
from .utils import add_page_numbers


class AddPageNumbersAPIView(BaseConversionAPIView):
    """Handle add page numbers to PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "ADD_PAGE_NUMBERS"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return AddPageNumbersSerializer

    def get_docs_decorator(self):
        return add_page_numbers_docs

    @add_page_numbers_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> Tuple[str, str]:
        """Add page numbers to PDF."""
        position = kwargs.get("position", "bottom-center")
        font_size = kwargs.get("font_size", 12)
        start_number = kwargs.get("start_number", 1)
        format_str = kwargs.get("format_str", "{page}")
        pdf_path, output_path = add_page_numbers(
            uploaded_file,
            position=position,
            font_size=font_size,
            start_number=start_number,
            format_str=format_str,
            suffix="_convertica",
        )
        return pdf_path, output_path
