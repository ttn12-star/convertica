# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import ProtectPDFSerializer
from .decorators import protect_pdf_docs
from .utils import protect_pdf
from ...base_views import BaseConversionAPIView


class ProtectPDFAPIView(BaseConversionAPIView):
    """Handle protect PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PROTECT_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return ProtectPDFSerializer

    def get_docs_decorator(self):
        return protect_pdf_docs

    @protect_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Protect PDF with password."""
        password = kwargs.get('password', '')
        user_password = kwargs.get('user_password')
        owner_password = kwargs.get('owner_password')
        pdf_path, output_path = protect_pdf(
            uploaded_file,
            password=password,
            user_password=user_password,
            owner_password=owner_password,
            suffix="_convertica"
        )
        return pdf_path, output_path

