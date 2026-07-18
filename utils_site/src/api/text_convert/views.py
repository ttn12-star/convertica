"""
Text to PDF conversion API view.

Renders pasted plain text to PDF by wrapping it in safe HTML and reusing the
Playwright HTML->PDF engine. Text input (no file upload), governed by the shared
daily quota via CONVERSION_TYPE.
"""

from django.http import HttpRequest

from ..base_views import BaseConversionAPIView
from .decorators import text_to_pdf_docs
from .serializers import TextToPDFSerializer
from .utils import convert_text_to_pdf


class TextToPDFAPIView(BaseConversionAPIView):
    """Handle pasted-text -> PDF conversion requests."""

    MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # text payload ceiling (2 MB)
    ALLOWED_CONTENT_TYPES = {"text/plain", "application/json"}
    CONVERSION_TYPE = "text_to_pdf"
    VALIDATE_PDF_PAGES = False  # no PDF input
    FILE_FIELD_REQUIRED = False  # uses `text` field, not a file upload

    def get_serializer_class(self):
        return TextToPDFSerializer

    def get_docs_decorator(self):
        return text_to_pdf_docs

    @text_to_pdf_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(self, _uploaded_file, context, **_kwargs) -> tuple[str, str]:
        request = context.get("request")
        serializer = self.get_serializer_class()(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return convert_text_to_pdf(
            data["text"],
            font=data.get("font", "sans"),
            font_size=data.get("font_size", 12),
            color=data.get("color", "#111111"),
            align=data.get("align", "left"),
            page_size=data.get("page_size", "A4"),
            margin=data.get("margin", "normal"),
            filename=data.get("filename", "document"),
        )

    def validate_file(self, _uploaded_file, _request) -> tuple[bool, str | None]:
        # Content is validated in the serializer, not as an uploaded file.
        return True, None

    def get_max_file_size(self, _request) -> int:
        return self.MAX_UPLOAD_SIZE
