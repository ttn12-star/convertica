"""API view for PDF to Markdown conversion."""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...daily_quota import try_consume_daily_quota
from .decorators import pdf_to_markdown_docs
from .serializers import PDFToMarkdownSerializer
from .utils import convert_pdf_to_markdown


class PDFToMarkdownAPIView(BaseConversionAPIView):
    """Handle PDF to Markdown conversion requests.

    Free for everyone, bounded by a daily quota (anonymous < registered <
    premium=unlimited). Large files stay premium via the standard size limits.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_MARKDOWN"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return PDFToMarkdownSerializer

    def get_docs_decorator(self):
        return pdf_to_markdown_docs

    @pdf_to_markdown_docs()
    def post(self, request: HttpRequest):
        allowed, quota_error = try_consume_daily_quota(request)
        if not allowed:
            return Response(
                {"error": quota_error}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return convert_pdf_to_markdown(
            uploaded_file=uploaded_file,
            detect_headings=kwargs.get("detect_headings", True),
            preserve_tables=kwargs.get("preserve_tables", True),
            suffix="_convertica",
        )

    def get_output_content_type(self, output_path: str) -> str:
        return "text/markdown; charset=utf-8"
