# views.py
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from .serializers import CompressPDFSerializer
from .decorators import compress_pdf_docs
from .utils import compress_pdf
from ...base_views import BaseConversionAPIView


class CompressPDFAPIView(BaseConversionAPIView):
    """Handle compress PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "COMPRESS_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return CompressPDFSerializer

    def get_docs_decorator(self):
        return compress_pdf_docs

    @compress_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Compress PDF."""
        compression_level = kwargs.get('compression_level', 'medium')
        pdf_path, output_path = compress_pdf(
            uploaded_file,
            compression_level=compression_level,
            suffix="_convertica"
        )
        return pdf_path, output_path

