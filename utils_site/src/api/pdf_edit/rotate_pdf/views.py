# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import rotate_pdf_docs
from .serializers import RotatePDFSerializer
from .utils import rotate_pdf


class RotatePDFAPIView(BaseConversionAPIView):
    """Handle PDF rotation requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "ROTATE_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return RotatePDFSerializer

    def get_docs_decorator(self):
        return rotate_pdf_docs

    @rotate_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform PDF rotation."""
        angle = kwargs.get("angle", 90)
        pages = kwargs.get("pages", "all")
        pdf_path, output_path = rotate_pdf(
            uploaded_file, angle=angle, pages=pages, suffix="_convertica"
        )
        return pdf_path, output_path
