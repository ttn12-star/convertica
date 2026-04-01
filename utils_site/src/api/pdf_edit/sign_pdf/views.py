# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .decorators import sign_pdf_docs
from .serializers import SignPDFSerializer
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


class SignPDFAPIView(BaseConversionAPIView):
    """Handle Sign PDF requests — add an image signature to a PDF page (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "sign_pdf"
    FILE_FIELD_NAME = "pdf_file"

    # Disable PDF page validation — done on the client side
    VALIDATE_PDF_PAGES = False

    from rest_framework.parsers import FormParser, MultiPartParser

    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return SignPDFSerializer

    def get_docs_decorator(self):
        return sign_pdf_docs

    @sign_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Add an image signature to the PDF."""
        from ...logging_utils import get_logger

        logger = get_logger(__name__)

        signature_image = kwargs.get("signature_image")
        position = kwargs.get("position", "bottom-right")
        all_pages = kwargs.get("all_pages", False)

        # page_number from serializer is 1-indexed; convert to 0-indexed for utils
        page_number_1indexed = kwargs.get("page_number", 1)
        try:
            page_number_1indexed = int(page_number_1indexed)
        except (ValueError, TypeError):
            page_number_1indexed = 1
        page_number = page_number_1indexed - 1

        # signature_width
        sig_width_val = kwargs.get("signature_width")
        if sig_width_val is not None:
            try:
                signature_width = int(sig_width_val)
            except (ValueError, TypeError):
                signature_width = 150
        else:
            signature_width = 150

        # opacity
        opacity_val = kwargs.get("opacity")
        if opacity_val is not None:
            try:
                opacity = float(opacity_val)
            except (ValueError, TypeError):
                opacity = 1.0
        else:
            opacity = 1.0

        logger.info(
            "SignPDFAPIView: position='%s', page_number=%d (0-indexed), "
            "signature_width=%d, opacity=%.2f, all_pages=%s, has_signature=%s",
            position,
            page_number,
            signature_width,
            opacity,
            all_pages,
            signature_image is not None,
            extra=context,
        )

        pdf_path, output_path = sign_pdf(
            uploaded_file,
            signature_image=signature_image,
            page_number=page_number,
            position=position,
            signature_width=signature_width,
            opacity=opacity,
            all_pages=all_pages,
            suffix="_signed",
        )
        return pdf_path, output_path
