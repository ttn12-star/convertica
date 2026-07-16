"""API views for EPUB conversion endpoints."""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ..base_views import BaseConversionAPIView
from .decorators import epub_to_pdf_docs, pdf_to_epub_docs
from .serializers import EPUBToPDFSerializer, PDFToEPUBSerializer
from .utils import convert_epub_to_pdf, convert_pdf_to_epub


class EPUBToPDFAPIView(BaseConversionAPIView):
    """Handle EPUB to PDF conversion requests.

    Free for everyone, bounded by a daily quota (anonymous < registered <
    premium=unlimited).
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/epub+zip",
        "application/zip",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".epub"}
    CONVERSION_TYPE = "EPUB_TO_PDF"
    FILE_FIELD_NAME = "epub_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return EPUBToPDFSerializer

    def get_docs_decorator(self):
        return epub_to_pdf_docs

    @epub_to_pdf_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return convert_epub_to_pdf(uploaded_file=uploaded_file, suffix="_convertica")


class PDFToEPUBAPIView(BaseConversionAPIView):
    """Handle PDF to EPUB conversion requests.

    Free for everyone, bounded by a daily quota (anonymous < registered <
    premium=unlimited).
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_EPUB"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return PDFToEPUBSerializer

    def get_docs_decorator(self):
        return pdf_to_epub_docs

    @pdf_to_epub_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return convert_pdf_to_epub(uploaded_file=uploaded_file, suffix="_convertica")

    def get_output_content_type(self, output_path: str) -> str:
        ext = output_path.lower().rsplit(".", 1)[-1] if "." in output_path else ""
        if ext == "epub":
            return "application/epub+zip"
        return super().get_output_content_type(output_path)
