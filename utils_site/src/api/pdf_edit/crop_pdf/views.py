# views.py
from typing import Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import crop_pdf_docs
from .serializers import CropPDFSerializer
from .utils import crop_pdf


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
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> Tuple[str, str]:
        """Crop PDF."""
        # Get and convert coordinates, handling string inputs
        # Check if value is in kwargs (not just using default)
        x_val = kwargs.get("x")
        if x_val is not None:
            try:
                x = float(x_val)
            except (ValueError, TypeError):
                x = 0.0
        else:
            x = 0.0

        y_val = kwargs.get("y")
        if y_val is not None:
            try:
                y = float(y_val)
            except (ValueError, TypeError):
                y = 0.0
        else:
            y = 0.0

        width_val = kwargs.get("width")
        if width_val is not None:
            try:
                width = float(width_val) if str(width_val).strip() else None
            except (ValueError, TypeError):
                width = None
        else:
            width = None

        height_val = kwargs.get("height")
        if height_val is not None:
            try:
                height = float(height_val) if str(height_val).strip() else None
            except (ValueError, TypeError):
                height = None
        else:
            height = None

        pages = kwargs.get("pages", "all")

        # Log all parameters for debugging
        from ...logging_utils import get_logger

        logger = get_logger(__name__)
        logger.info(
            f"CropPDFAPIView: x={x}, y={y}, width={width}, height={height}, pages='{pages}'",
            extra=context,
        )

        pdf_path, output_path = crop_pdf(
            uploaded_file,
            x=x,
            y=y,
            width=width,
            height=height,
            pages=pages,
            suffix="_convertica",
        )
        return pdf_path, output_path
