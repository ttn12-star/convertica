"""
Batch PDF watermark API views.

Supports processing up to 10 PDF files simultaneously for premium users.
All files are watermarked with the same parameters and returned as a ZIP archive.
"""

from django.http import HttpRequest
from src.api.rate_limit_utils import combined_rate_limit

from ...base_views import BaseConversionAPIView
from .batch_serializers import AddWatermarkBatchSerializer
from .decorators import add_watermark_docs
from .utils import add_watermark


class AddWatermarkBatchAPIView(BaseConversionAPIView):
    """Handle batch PDF watermark requests."""

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "add_watermark_batch"
    FILE_FIELD_NAME = "pdf_files"
    VALIDATE_PDF_PAGES = False  # Client-side validation

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return AddWatermarkBatchSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return add_watermark_docs

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @add_watermark_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        """Add watermark to PDF with specified parameters."""
        watermark_type = kwargs.get("watermark_type", "text")
        watermark_text = kwargs.get("watermark_text", "CONFIDENTIAL")
        watermark_image = kwargs.get("watermark_image")
        x = float(kwargs.get("x", 0))
        y = float(kwargs.get("y", 0))
        opacity = float(kwargs.get("opacity", 0.3))
        rotation = float(kwargs.get("rotation", 0))
        scale = float(kwargs.get("scale", 1.0))
        color = kwargs.get("color", "#000000")
        font_size = int(kwargs.get("font_size", 72))
        pages = kwargs.get("pages", "all")

        input_path, output_path = add_watermark(
            uploaded_file=uploaded_file,
            watermark_type=watermark_type,
            watermark_text=watermark_text,
            watermark_image=watermark_image,
            x=x,
            y=y,
            opacity=opacity,
            rotation=rotation,
            scale=scale,
            color=color,
            font_size=font_size,
            pages=pages,
            suffix="_watermarked",
        )

        return input_path, output_path
