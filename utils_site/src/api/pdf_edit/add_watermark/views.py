# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import add_watermark_docs
from .serializers import AddWatermarkSerializer
from .utils import add_watermark


class AddWatermarkAPIView(BaseConversionAPIView):
    """Handle add watermark to PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "ADD_WATERMARK"
    FILE_FIELD_NAME = "pdf_file"

    # Explicitly enable PDF page validation for watermark operations
    VALIDATE_PDF_PAGES = True

    # Explicitly set parser classes to avoid auto-detection of request body
    from rest_framework.parsers import FormParser, MultiPartParser

    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return AddWatermarkSerializer

    def get_docs_decorator(self):
        return add_watermark_docs

    @add_watermark_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Add watermark to PDF."""
        watermark_text = kwargs.get("watermark_text", "CONFIDENTIAL")
        watermark_file = kwargs.get("watermark_file")
        position = kwargs.get("position", "diagonal")

        # Convert coordinates, handling string inputs
        # Support both 'x'/'y' and 'x_coordinate'/'y_coordinate' field names
        x_str = kwargs.get("x") or kwargs.get("x_coordinate")
        y_str = kwargs.get("y") or kwargs.get("y_coordinate")
        try:
            x = float(x_str) if x_str and str(x_str).strip() else None
        except (ValueError, TypeError):
            x = None
        try:
            y = float(y_str) if y_str and str(y_str).strip() else None
        except (ValueError, TypeError):
            y = None

        color = kwargs.get("color", "#000000")

        # Convert opacity, rotation, scale
        # Check if value is in kwargs (not just using default)
        opacity_val = kwargs.get("opacity")
        if opacity_val is not None:
            try:
                opacity = float(opacity_val)
            except (ValueError, TypeError):
                opacity = 0.3
        else:
            opacity = 0.3

        font_size_val = kwargs.get("font_size")
        if font_size_val is not None:
            try:
                font_size = int(font_size_val)
            except (ValueError, TypeError):
                font_size = 72
        else:
            font_size = 72

        # Support both 'rotation' and 'rotation_angle' field names
        rotation_val = kwargs.get("rotation") or kwargs.get("rotation_angle")
        if rotation_val is not None:
            try:
                rotation = float(rotation_val)
            except (ValueError, TypeError):
                rotation = 0.0
        else:
            rotation = 0.0

        scale_val = kwargs.get("scale")
        if scale_val is not None:
            try:
                scale = float(scale_val)
            except (ValueError, TypeError):
                scale = 1.0
        else:
            scale = 1.0

        pages = kwargs.get("pages", "all")

        # Log all parameters for debugging
        from ...logging_utils import get_logger

        logger = get_logger(__name__)
        logger.info(
            "AddWatermarkAPIView: watermark_text='%s', has_file=%s, "
            "position='%s', x=%s, y=%s, color='%s', opacity=%s, "
            "font_size=%s, rotation=%s, scale=%s, pages='%s'",
            watermark_text,
            watermark_file is not None,
            position,
            x,
            y,
            color,
            opacity,
            font_size,
            rotation,
            scale,
            pages,
            extra=context,
        )

        pdf_path, output_path = add_watermark(
            uploaded_file,
            watermark_text=watermark_text,
            watermark_file=watermark_file,
            position=position,
            x=x,
            y=y,
            color=color,
            opacity=opacity,
            font_size=font_size,
            rotation=rotation,
            scale=scale,
            pages=pages,
            suffix="_convertica",
        )
        return pdf_path, output_path
