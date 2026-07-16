"""Image to Text (OCR) API view.

Free tool with tiered limits:
- Free: small per-image size cap, .txt output; daily count comes from the
  global DailyQuotaMiddleware bucket shared by all tools.
- Premium: large images, unlimited daily use, and .docx (Word) export.
"""

import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .decorators import image_to_text_docs
from .serializers import ImageToTextSerializer
from .utils import run_image_ocr


class ImageToTextAPIView(BaseConversionAPIView):
    """Extract text from an uploaded image and return it as .txt (free) or .docx (premium)."""

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
        premium = is_premium_active(request.user)

        # Word (.docx) export is a Premium feature.
        output_format = (request.data.get("output_format") or "txt").lower()
        if output_format == "docx" and not premium:
            return Response(
                {
                    "error": _(
                        "Word (.docx) export is a Premium feature. Upgrade to "
                        "download your text as a Word document."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not premium:
            # Free per-image size cap (smaller than the global free limit; almost
            # every photo/screenshot/scan fits, and it makes Premium's larger
            # limit a real benefit).
            uploaded = request.FILES.get(self.FILE_FIELD_NAME)
            free_max = settings.IMAGE_TO_TEXT_FREE_MAX_BYTES
            if uploaded is not None and uploaded.size > free_max:
                return Response(
                    {
                        "error": _(
                            "Image too large (%(file_mb).1f MB). Free limit is "
                            "%(free_mb).0f MB. Upgrade to Premium for larger images, "
                            "unlimited daily use, and Word export."
                        )
                        % {
                            "file_mb": uploaded.size / (1024 * 1024),
                            "free_mb": free_max / (1024 * 1024),
                        }
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return run_image_ocr(
            uploaded_file,
            language=kwargs.get("language", "auto"),
            confidence_threshold=kwargs.get("confidence_threshold", 60),
            output_format=kwargs.get("output_format", "txt"),
        )

    def get_output_content_type(self, output_path: str) -> str:
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".txt":
            return "text/plain; charset=utf-8"
        if ext == ".docx":
            return (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
        return "application/octet-stream"
