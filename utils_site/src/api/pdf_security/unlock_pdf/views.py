# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import unlock_pdf_docs
from .serializers import UnlockPDFSerializer
from .utils import unlock_pdf


class UnlockPDFAPIView(BaseConversionAPIView):
    """Handle unlock PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "UNLOCK_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return UnlockPDFSerializer

    def get_docs_decorator(self):
        return unlock_pdf_docs

    @unlock_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Unlock PDF by removing password."""
        password = kwargs.get("password", "")
        pdf_path, output_path = unlock_pdf(
            uploaded_file, password=password, suffix="_convertica"
        )
        return pdf_path, output_path
