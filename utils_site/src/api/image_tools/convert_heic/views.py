"""HEIC / HEIF converter API view (free single-file, daily-quota limited)."""

import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import convert_heic_docs
from .serializers import ConvertHEICSerializer
from .utils import convert_heic


class ConvertHEICAPIView(BaseConversionAPIView):
    """Convert Apple HEIC / HEIF photos to JPG, PNG, or PDF.

    Free for everyone as a single-file conversion, bounded by a daily quota
    (anonymous < registered < premium=unlimited). Batch mode stays premium.
    """

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
