# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import JPGToPDFSerializer
from .decorators import jpg_to_pdf_docs
from .utils import convert_jpg_to_pdf
from ...base_views import BaseConversionAPIView


class JPGToPDFAPIView(BaseConversionAPIView):
    """Handle JPG/JPEG → PDF conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
    CONVERSION_TYPE = "JPG_TO_PDF"
    FILE_FIELD_NAME = "image_file"

    def get_serializer_class(self):
        return JPGToPDFSerializer

    def get_docs_decorator(self):
        return jpg_to_pdf_docs

    @jpg_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Perform JPG to PDF conversion."""
        image_path, pdf_path = convert_jpg_to_pdf(
            uploaded_file,
            suffix="_convertica"
        )
        return image_path, pdf_path
