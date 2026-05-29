# views.py
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import generate_favicon_docs
from .serializers import GenerateFaviconSerializer
from .utils import generate_favicon


class GenerateFaviconAPIView(BaseConversionAPIView):
    """Generate a complete favicon package (ZIP) from one source image."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
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
        ".svg",
    }
    CONVERSION_TYPE = "generate_favicon"
    FILE_FIELD_NAME = "image_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return GenerateFaviconSerializer

    def get_docs_decorator(self):
        return generate_favicon_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to generate a favicon."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @generate_favicon_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return generate_favicon(uploaded_file)

    def get_output_content_type(self, output_path: str) -> str:
        return "application/zip"
