"""
Batch Sign PDF API views.

Supports signing up to 10 PDF files simultaneously for premium users.
The same signature image is applied to all files, which are returned as a ZIP archive.
"""

from django.conf import settings
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from src.api.rate_limit_utils import combined_rate_limit

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .batch_serializers import SignPDFBatchSerializer
from .decorators import sign_pdf_docs
from .utils import sign_pdf


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


class SignPDFBatchAPIView(BaseConversionAPIView):
    """Handle batch Sign PDF requests (premium only)."""

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "sign_pdf_batch"
    FILE_FIELD_NAME = "pdf_files"
    VALIDATE_PDF_PAGES = False  # Client-side validation

    def get_serializer_class(self):
        """Return appropriate serializer for this view."""
        return SignPDFBatchSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return sign_pdf_docs

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @sign_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        """Add an image signature to a single PDF within the batch."""
        signature_image = kwargs.get("signature_image")
        position = kwargs.get("position", "bottom-right")
        all_pages = kwargs.get("all_pages", False)

        # page_number from serializer is 1-indexed; convert to 0-indexed
        page_number_1indexed = kwargs.get("page_number", 1)
        try:
            page_number_1indexed = int(page_number_1indexed)
        except (ValueError, TypeError):
            page_number_1indexed = 1
        page_number = page_number_1indexed - 1

        try:
            signature_width = int(kwargs.get("signature_width", 150))
        except (ValueError, TypeError):
            signature_width = 150

        try:
            opacity = float(kwargs.get("opacity", 1.0))
        except (ValueError, TypeError):
            opacity = 1.0

        # Reset the signature image file pointer so each PDF in the batch can read it
        if hasattr(signature_image, "seek"):
            signature_image.seek(0)

        input_path, output_path = sign_pdf(
            pdf_file=uploaded_file,
            signature_image=signature_image,
            page_number=page_number,
            position=position,
            signature_width=signature_width,
            opacity=opacity,
            all_pages=all_pages,
            suffix="_signed",
        )

        return input_path, output_path
