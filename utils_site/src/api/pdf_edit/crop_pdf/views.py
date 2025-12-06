# views.py
from typing import Tuple, Optional

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import CropPDFSerializer
from .decorators import crop_pdf_docs
from .utils import crop_pdf
from ...base_views import BaseConversionAPIView


class CropPDFAPIView(BaseConversionAPIView):
    """Handle PDF cropping requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "CROP_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return CropPDFSerializer

    def get_docs_decorator(self):
        return crop_pdf_docs

    @crop_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Crop PDF."""
        x = kwargs.get('x', 0.0)
        y = kwargs.get('y', 0.0)
        width = kwargs.get('width')
        height = kwargs.get('height')
        pages = kwargs.get('pages', 'all')
        pdf_path, output_path = crop_pdf(
            uploaded_file,
            x=x,
            y=y,
            width=width,
            height=height,
            pages=pages,
            suffix="_convertica"
        )
        return pdf_path, output_path

