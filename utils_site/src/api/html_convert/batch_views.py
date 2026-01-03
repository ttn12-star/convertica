"""
Batch HTML to PDF conversion API views.

Supports processing up to 20 HTML files simultaneously for premium users.
Uses async processing for better performance with multiple files.
"""

from django.http import HttpRequest
from src.api.rate_limit_utils import combined_rate_limit

from ..base_views import BaseConversionAPIView
from .decorators import html_to_pdf_docs
from .serializers import HTMLToPDFSerializer
from .utils import convert_html_to_pdf


class HTMLToPDFBatchAPIView(BaseConversionAPIView):
    """Handle batch HTML content → PDF conversion requests."""

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per HTML content
    ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/json"}
    CONVERSION_TYPE = "html_to_pdf_batch"
    VALIDATE_PDF_PAGES = False  # Not applicable for HTML content

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return HTMLToPDFSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return html_to_pdf_docs

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @html_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(self, _uploaded_file, context, **_kwargs) -> tuple[str, str]:
        """Convert HTML content to PDF."""
        request = context.get("request")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
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

    def validate_file(self, uploaded_file, request) -> tuple[bool, str | None]:
        """Validate HTML content before conversion."""
        # For HTML conversion, we validate the content directly in perform_conversion
        return True, None

    def get_max_file_size(self, request) -> int:
        """Get maximum file size for HTML content."""
        # HTML content is typically smaller, use conservative limit
        return self.MAX_UPLOAD_SIZE
