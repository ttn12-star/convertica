"""Image to Text (OCR) API view — free, no premium gate."""

import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import image_to_text_docs
from .serializers import ImageToTextSerializer
from .utils import run_image_ocr


class ImageToTextAPIView(BaseConversionAPIView):
    """Extract text from an uploaded image and return it as a .txt file."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    # HEIC/HEIF often arrive as application/octet-stream; whitelist by extension.
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
        "image/heic",
        "image/heif",
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
        ".heic",
        ".heif",
    }
    CONVERSION_TYPE = "image_to_text"
    FILE_FIELD_NAME = "image_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ImageToTextSerializer

    def get_docs_decorator(self):
        return image_to_text_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to extract text."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @image_to_text_docs()
    def post(self, request: HttpRequest):
        # Free tool: no premium gate. The base view's OCR premium gate only fires
        # when context['ocr_enabled'] is set, which this serializer never sends.
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        language = kwargs.get("language", "auto")
        confidence_threshold = kwargs.get("confidence_threshold", 60)
        return run_image_ocr(
            uploaded_file,
            language=language,
            confidence_threshold=confidence_threshold,
        )

    def get_output_content_type(self, output_path: str) -> str:
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".txt":
            return "text/plain; charset=utf-8"
        return "application/octet-stream"
