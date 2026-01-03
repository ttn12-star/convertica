"""
HTML to PDF conversion API views.

Converts HTML content and URLs to PDF using Playwright.
Supports both single file and batch processing for premium users.
"""

from django.http import HttpRequest

from ..base_views import BaseConversionAPIView
from .decorators import html_to_pdf_docs, url_to_pdf_docs
from .serializers import HTMLToPDFSerializer, URLToPDFSerializer
from .utils import convert_html_to_pdf, convert_url_to_pdf


class HTMLToPDFAPIView(BaseConversionAPIView):
    """Handle HTML content → PDF conversion requests."""

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB for HTML content
    ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/json"}
    CONVERSION_TYPE = "html_to_pdf"
    VALIDATE_PDF_PAGES = False  # Not applicable for HTML content
    FILE_FIELD_REQUIRED = False  # HTML conversion uses content field, not file upload

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return HTMLToPDFSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return html_to_pdf_docs

    @html_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, _uploaded_file, context, **_kwargs) -> tuple[str, str]:
        """Convert HTML content to PDF."""
        request = context.get("request")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        html_content = serializer.validated_data["html_content"]
        filename = serializer.validated_data.get("filename", "converted")

        # Extract PDF options
        options = {
            "format": serializer.validated_data.get("page_size", "A4"),
            "margin": {
                "top": serializer.validated_data.get("margin_top", "1cm"),
                "bottom": serializer.validated_data.get("margin_bottom", "1cm"),
                "left": serializer.validated_data.get("margin_left", "1cm"),
                "right": serializer.validated_data.get("margin_right", "1cm"),
            },
        }

        html_path, output_path = convert_html_to_pdf(
            html_content, filename=filename, suffix="_convertica", **options
        )
        return html_path, output_path

    def validate_file(self, _uploaded_file, _request) -> tuple[bool, str | None]:
        """Validate HTML content before conversion."""
        # For HTML conversion, we validate the content directly in perform_conversion
        return True, None

    def get_max_file_size(self, _request) -> int:
        """Get maximum file size for HTML content."""
        # HTML content is typically smaller, use conservative limit
        return self.MAX_UPLOAD_SIZE


class URLToPDFAPIView(BaseConversionAPIView):
    """Handle URL → PDF conversion requests."""

    MAX_UPLOAD_SIZE = 0  # No file upload for URL conversion
    ALLOWED_CONTENT_TYPES = set()
    CONVERSION_TYPE = "url_to_pdf"
    VALIDATE_PDF_PAGES = False  # Not applicable for URL conversion
    FILE_FIELD_REQUIRED = False  # URL conversion doesn't need file upload

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return URLToPDFSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return url_to_pdf_docs

    @url_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, _uploaded_file, context, **_kwargs) -> tuple[str, str]:
        """Convert URL to PDF."""
        request = context.get("request")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        filename = serializer.validated_data.get("filename", "converted")

        # Extract PDF options
        options = {
            "format": serializer.validated_data.get("page_size", "A4"),
            "margin": {
                "top": serializer.validated_data.get("margin_top", "1cm"),
                "bottom": serializer.validated_data.get("margin_bottom", "1cm"),
                "left": serializer.validated_data.get("margin_left", "1cm"),
                "right": serializer.validated_data.get("margin_right", "1cm"),
            },
        }

        url, output_path = convert_url_to_pdf(
            url, filename=filename, suffix="_convertica", **options
        )
        return url, output_path

    def validate_file(self, _uploaded_file, _request) -> tuple[bool, str | None]:
        """Not applicable for URL conversion."""
        return True, None

    def get_max_file_size(self, _request) -> int:
        """Not applicable for URL conversion."""
        return 0
