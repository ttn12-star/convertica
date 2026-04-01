# views.py
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import optimize_image_docs
from .serializers import OptimizeImageSerializer
from .utils import optimize_image


class OptimizeImageAPIView(BaseConversionAPIView):
    """Handle image optimization requests.

    Supports JPEG, PNG, WebP, and GIF images.
    Reduces file size while maintaining configurable quality.
    Optionally resizes images to fit within max dimensions.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    CONVERSION_TYPE = "optimize_image"
    FILE_FIELD_NAME = "image_file"

    # Images are not PDFs — skip PDF page validation entirely
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return OptimizeImageSerializer

    def get_docs_decorator(self):
        return optimize_image_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to optimize images."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @optimize_image_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform image optimization."""
        quality = kwargs.get("quality", 85)
        output_format = kwargs.get("output_format") or None
        max_width = kwargs.get("max_width") or None
        max_height = kwargs.get("max_height") or None

        return optimize_image(
            uploaded_file,
            quality=quality,
            output_format=output_format,
            max_width=max_width,
            max_height=max_height,
        )

    def get_output_content_type(self, output_path: str) -> str:
        import os

        ext = os.path.splitext(output_path)[1].lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return content_types.get(ext, "application/octet-stream")
