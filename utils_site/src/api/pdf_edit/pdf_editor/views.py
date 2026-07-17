# views.py
"""PDF Editor endpoint — full visual editor op-set on one PDF.

Reuses the Add Text serializer and materializer; distinct CONVERSION_TYPE
so OperationRun metrics separate the head-cluster editor from the add-text
satellite. Free under the global daily quota; no batch (overlay across
differing files is meaningless).
"""
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework.parsers import FormParser, MultiPartParser

from ...base_views import BaseConversionAPIView
from ..add_text.serializers import AddTextPDFSerializer
from ..add_text.utils import add_text_pdf
from .decorators import pdf_editor_docs


class PdfEditorAPIView(BaseConversionAPIView):
    """Place text/image/signature/shape/ink/whiteout/highlight on a PDF."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "pdf_editor"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = False

    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return AddTextPDFSerializer

    def get_docs_decorator(self):
        return pdf_editor_docs

    @pdf_editor_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(self, uploaded_file: UploadedFile, context: dict, **kwargs):
        operations = kwargs.get("operations") or []
        return add_text_pdf(uploaded_file, operations=operations, suffix="_edited")
