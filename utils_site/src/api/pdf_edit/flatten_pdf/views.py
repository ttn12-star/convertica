# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import flatten_pdf_docs
from .serializers import FlattenPDFSerializer
from .utils import flatten_pdf


class FlattenPDFAPIView(BaseConversionAPIView):
    """Handle PDF flatten requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "FLATTEN_PDF"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return FlattenPDFSerializer

    def get_docs_decorator(self):
        return flatten_pdf_docs

    @flatten_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Flatten PDF by removing form fields and annotations."""
        return flatten_pdf(
            uploaded_file,
            suffix="_convertica",
        )
