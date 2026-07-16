# views.py
"""Single-file Sign PDF endpoint.

The browser editor sends a PDF plus a JSON `signatures` array describing
where each signature image lives. Free for everyone under the global daily
quota; batch signing stays premium.
"""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework.parsers import FormParser, MultiPartParser

from ...base_views import BaseConversionAPIView
from .decorators import sign_pdf_docs
from .serializers import SignPDFSerializer
from .utils import sign_pdf


class SignPDFAPIView(BaseConversionAPIView):
    """Add one or more image signatures to a PDF (free, global daily quota)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "sign_pdf"
    FILE_FIELD_NAME = "pdf_file"

    # Client-side validation only — the visual editor knows the page count.
    VALIDATE_PDF_PAGES = False

    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return SignPDFSerializer

    def get_docs_decorator(self):
        return sign_pdf_docs

    @sign_pdf_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        signatures = kwargs.get("signatures") or []
        return sign_pdf(uploaded_file, signatures=signatures, suffix="_signed")
