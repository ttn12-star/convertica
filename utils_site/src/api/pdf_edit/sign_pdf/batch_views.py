"""
Batch Sign PDF API view.

Applies one signature image to up to 10 PDFs simultaneously (premium only).
The batch flow uses the enum-position contract (`bottom-right`, `center`,
…) instead of per-coordinate placement, because per-file coordinates would
not make sense when each file has different dimensions.
"""

from django.conf import settings
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from src.api.rate_limit_utils import combined_rate_limit

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .batch_serializers import SignPDFBatchSerializer
from .decorators import sign_pdf_batch_docs
from .utils import apply_simple_signature_to_pdf


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
    """Apply one signature to many PDFs (premium only)."""

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "sign_pdf_batch"
    FILE_FIELD_NAME = "pdf_files"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return SignPDFBatchSerializer

    def get_docs_decorator(self):
        return sign_pdf_batch_docs

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @sign_pdf_batch_docs()
    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def perform_conversion(self, uploaded_file, context, **kwargs) -> tuple[str, str]:
        signature_image = kwargs.get("signature_image")
        position = kwargs.get("position", "bottom-right")
        all_pages = kwargs.get("all_pages", False)

        try:
            page_number = int(kwargs.get("page_number", 1)) - 1
        except (ValueError, TypeError):
            page_number = 0
        try:
            signature_width = int(kwargs.get("signature_width", 150))
        except (ValueError, TypeError):
            signature_width = 150
        try:
            opacity = float(kwargs.get("opacity", 1.0))
        except (ValueError, TypeError):
            opacity = 1.0

        # Each PDF in the batch reads the same signature image; rewind it.
        if hasattr(signature_image, "seek"):
            signature_image.seek(0)

        return apply_simple_signature_to_pdf(
            pdf_file=uploaded_file,
            signature_image=signature_image,
            page_number=page_number,
            position=position,
            signature_width=signature_width,
            opacity=opacity,
            all_pages=all_pages,
            suffix="_signed",
        )
