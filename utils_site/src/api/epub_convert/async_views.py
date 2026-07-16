"""Async API views for premium EPUB conversion endpoints."""

from django.conf import settings
from django.http import HttpRequest
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from src.tasks.pdf_conversion import generic_conversion_task

from ..async_views import AsyncConversionAPIView
from ..daily_quota import try_consume_daily_quota
from .serializers import EPUBToPDFSerializer, PDFToEPUBSerializer

# Shared response docs for the async conversion endpoints. Free for everyone
# under a daily quota (429 when exceeded); large files still 413.
_ASYNC_RESPONSES = {
    202: "Conversion task accepted (poll /api/tasks/<id>/status/).",
    400: "Bad request - invalid file or parameters.",
    413: "File too large.",
    429: "Daily free limit reached (log in / upgrade for more).",
}


def _quota_error(request: HttpRequest) -> Response | None:
    """Consume one daily-quota unit; return a 429 Response if over the limit."""
    allowed, message = try_consume_daily_quota(request)
    if allowed:
        return None
    return Response({"error": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class EPUBToPDFAsyncAPIView(AsyncConversionAPIView):
    """Async EPUB to PDF conversion (free, daily-quota limited)."""

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

    @swagger_auto_schema(
        operation_summary="EPUB to PDF (async)",
        tags=["PDF Conversion"],
        responses=_ASYNC_RESPONSES,
    )
    def post(self, request: HttpRequest):
        over_quota = _quota_error(request)
        if over_quota is not None:
            return over_quota
        return super().post(request)


class PDFToEPUBAsyncAPIView(AsyncConversionAPIView):
    """Async PDF to EPUB conversion (free, daily-quota limited)."""

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

    @swagger_auto_schema(
        operation_summary="PDF to EPUB (async)",
        tags=["PDF Conversion"],
        responses=_ASYNC_RESPONSES,
    )
    def post(self, request: HttpRequest):
        over_quota = _quota_error(request)
        if over_quota is not None:
            return over_quota
        return super().post(request)
