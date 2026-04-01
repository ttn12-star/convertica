# views.py
import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import convert_image_docs
from .serializers import ConvertImageSerializer
from .utils import EXTENSIONS, convert_image


class ConvertImageAPIView(BaseConversionAPIView):
    """Handle image format conversion requests.

    Converts between JPEG, PNG, WebP, GIF, BMP, and TIFF formats.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
    }
    CONVERSION_TYPE = "convert_image"
    FILE_FIELD_NAME = "image_file"

    # Images are not PDFs — skip PDF page validation entirely
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ConvertImageSerializer

    def get_docs_decorator(self):
        return convert_image_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to convert images."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @convert_image_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform image format conversion."""
        output_format = kwargs.get("output_format", "JPEG")
        quality = kwargs.get("quality", 90)

        return convert_image(
            uploaded_file,
            output_format=output_format,
            quality=quality,
        )

    def get_output_content_type(self, output_path: str) -> str:
        ext = os.path.splitext(output_path)[1].lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        return content_types.get(ext, "application/octet-stream")
