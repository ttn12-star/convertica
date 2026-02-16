"""Async API views for premium EPUB conversion endpoints."""

from django.conf import settings
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from src.tasks.pdf_conversion import generic_conversion_task

from ..async_views import AsyncConversionAPIView
from ..premium_utils import is_premium_active
from .serializers import EPUBToPDFSerializer, PDFToEPUBSerializer


def _premium_access_error(request: HttpRequest) -> Response:
    """Build premium-required API response."""
    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
    if not request.user.is_authenticated:
        if payments_enabled:
            message = "This converter is available for premium users. Please log in and upgrade."
        else:
            message = "This converter is currently unavailable."
    else:
        if payments_enabled:
            message = "This converter is available for premium users. Upgrade to Premium to continue."
        else:
            message = "This converter is currently unavailable."
    return Response({"error": message}, status=status.HTTP_403_FORBIDDEN)


class EPUBToPDFAsyncAPIView(AsyncConversionAPIView):
    """Async EPUB to PDF conversion (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/epub+zip",
        "application/zip",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".epub"}
    CONVERSION_TYPE = "epub_to_pdf"
    FILE_FIELD_NAME = "epub_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return EPUBToPDFSerializer

    def get_celery_task(self):
        return generic_conversion_task

    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)


class PDFToEPUBAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to EPUB conversion (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_to_epub"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return PDFToEPUBSerializer

    def get_celery_task(self):
        return generic_conversion_task

    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)
