# views.py
"""Single-file Add Text to PDF endpoint.

The browser editor sends a PDF plus a JSON `operations` array describing
each placed object (text box, whiteout, highlight). Free for everyone
under the global daily quota; batch is deliberately absent in V1 — a
coordinate overlay makes little sense across files of different sizes
(same reasoning as sign_pdf's enum-position batch contract).
"""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework.parsers import FormParser, MultiPartParser

from ...base_views import BaseConversionAPIView
from .decorators import add_text_pdf_docs
from .serializers import AddTextPDFSerializer
from .utils import add_text_pdf


class AddTextPDFAPIView(BaseConversionAPIView):
    """Place text/whiteout/highlight objects on a PDF (free, daily quota)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "add_text_pdf"
    FILE_FIELD_NAME = "pdf_file"

    # Client-side validation only — the visual editor knows the page count.
    VALIDATE_PDF_PAGES = False

    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return AddTextPDFSerializer

    def get_docs_decorator(self):
        return add_text_pdf_docs

    @add_text_pdf_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        operations = kwargs.get("operations") or []
        return add_text_pdf(uploaded_file, operations=operations, suffix="_edited")
