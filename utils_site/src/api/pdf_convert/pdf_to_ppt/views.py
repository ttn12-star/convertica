"""API views for PDF to PowerPoint conversion."""

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import pdf_to_ppt_docs
from .serializers import PDFToPowerPointSerializer
from .utils import convert_pdf_to_ppt


class PDFToPowerPointAPIView(BaseConversionAPIView):
    """Handle PDF to PowerPoint conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PDF_TO_PPT"
    FILE_FIELD_NAME = "pdf_file"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        """Return serializer class for this view."""
        return PDFToPowerPointSerializer

    def get_docs_decorator(self):
        """Return Swagger documentation decorator for this view."""
        return pdf_to_ppt_docs

    @pdf_to_ppt_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Convert PDF to PowerPoint."""
        extract_images = kwargs.get("extract_images", True)

        input_path, output_path = convert_pdf_to_ppt(
            uploaded_file=uploaded_file,
            extract_images=extract_images,
            suffix="_convertica",
        )

        return input_path, output_path
