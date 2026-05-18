"""HEIC / HEIF converter API view (premium-gated)."""

import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .decorators import convert_heic_docs
from .serializers import ConvertHEICSerializer
from .utils import convert_heic


def _premium_access_error(request: HttpRequest) -> Response:
    """Build premium-required API response (mirrors PDFToText pattern)."""
    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
    if not request.user.is_authenticated:
        if payments_enabled:
            message = (
                "This converter is available for premium users. "
                "Please log in and upgrade."
            )
        else:
            message = "This converter is currently unavailable."
    else:
        if payments_enabled:
            message = (
                "This converter is available for premium users. "
                "Upgrade to Premium to continue."
            )
        else:
            message = "This converter is currently unavailable."
    return Response({"error": message}, status=status.HTTP_403_FORBIDDEN)


class ConvertHEICAPIView(BaseConversionAPIView):
    """Convert Apple HEIC / HEIF photos to JPG, PNG, or PDF (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    # HEIC files don't always carry a stable MIME — Safari/Edge sometimes send
    # "application/octet-stream" — so we whitelist by extension and accept the
    # generic content type alongside the canonical "image/heic" / "image/heif".
    ALLOWED_CONTENT_TYPES = {
        "image/heic",
        "image/heif",
        "image/heic-sequence",
        "image/heif-sequence",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".heic", ".heif"}
    CONVERSION_TYPE = "convert_heic"
    FILE_FIELD_NAME = "image_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ConvertHEICSerializer

    def get_docs_decorator(self):
        return convert_heic_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to convert HEIC images."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @convert_heic_docs()
    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        output_format = kwargs.get("output_format", "JPEG")
        quality = kwargs.get("quality", 90)
        return convert_heic(
            uploaded_file,
            output_format=output_format,
            quality=quality,
        )

    def get_output_content_type(self, output_path: str) -> str:
        ext = os.path.splitext(output_path)[1].lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }.get(ext, "application/octet-stream")
