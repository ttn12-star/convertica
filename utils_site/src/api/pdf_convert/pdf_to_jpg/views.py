# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...logging_utils import get_logger, log_file_validation_error
from .decorators import pdf_to_jpg_docs
from .serializers import PDFToJPGSerializer
from .utils import convert_pdf_to_jpg

logger = get_logger(__name__)


class PDFToJPGAPIView(BaseConversionAPIView):
    """Handle PDF → JPG conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_JPG"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False  # Client-side validation implemented

    def get_serializer_class(self):
        return PDFToJPGSerializer

    def get_docs_decorator(self):
        return pdf_to_jpg_docs

    @pdf_to_jpg_docs()
    async def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return await self.post_async(request)

    def validate_file_additional(
        self, uploaded_file: UploadedFile, context: dict, validated_data: dict
    ) -> Response | None:
        """Validate DPI parameter."""
        dpi = validated_data.get("dpi", 300)
        if dpi < 150 or dpi > 600:
            log_file_validation_error(
                logger,
                f"DPI out of range: {dpi}",
                context,
            )
            return Response(
                {
                    "error": "DPI must be between 150 and 600. Recommended: 300 DPI for high quality."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    async def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform PDF to JPG conversion (selected pages to ZIP)."""
        pages = kwargs.get("pages", "all")
        dpi = kwargs.get("dpi", 300)

        pdf_path, zip_path = await convert_pdf_to_jpg(
            uploaded_file, pages=pages, dpi=dpi, suffix="_convertica"
        )
        return pdf_path, zip_path
