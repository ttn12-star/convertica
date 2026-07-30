# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import resize_pdf_docs
from .serializers import ResizePDFSerializer
from .utils import resize_pdf


class ResizePDFAPIView(BaseConversionAPIView):
    """Handle PDF page-size change requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "RESIZE_PDF"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ResizePDFSerializer

    def get_docs_decorator(self):
        return resize_pdf_docs

    @resize_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Place the PDF's pages on a different paper size."""
        return resize_pdf(
            uploaded_file,
            target_size=kwargs.get("target_size", "letter"),
            mode=kwargs.get("mode", "auto"),
            suffix="_convertica",
        )
