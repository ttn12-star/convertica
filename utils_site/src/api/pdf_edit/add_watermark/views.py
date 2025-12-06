# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import AddWatermarkSerializer
from .decorators import add_watermark_docs
from .utils import add_watermark
from ...base_views import BaseConversionAPIView


class AddWatermarkAPIView(BaseConversionAPIView):
    """Handle add watermark to PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "ADD_WATERMARK"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return AddWatermarkSerializer

    def get_docs_decorator(self):
        return add_watermark_docs

    @add_watermark_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Add watermark to PDF."""
        watermark_text = kwargs.get('watermark_text', 'CONFIDENTIAL')
        watermark_file = kwargs.get('watermark_file')
        position = kwargs.get('position', 'diagonal')
        opacity = kwargs.get('opacity', 0.3)
        font_size = kwargs.get('font_size', 72)
        pdf_path, output_path = add_watermark(
            uploaded_file,
            watermark_text=watermark_text,
            watermark_file=watermark_file,
            position=position,
            opacity=opacity,
            font_size=font_size,
            suffix="_convertica"
        )
        return pdf_path, output_path

