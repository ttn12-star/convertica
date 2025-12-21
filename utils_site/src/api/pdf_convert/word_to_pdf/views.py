# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from utils_site.src.tasks.pdf_conversion import convert_word_to_pdf_task

from ...base_views import BaseConversionAPIView
from .decorators import word_to_pdf_docs
from .serializers import WordToPDFSerializer
from .utils import convert_word_to_pdf


class WordToPDFAPIView(BaseConversionAPIView):
    """Handle Word (.doc/.docx) → PDF conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".doc", ".docx"}
    CONVERSION_TYPE = "WORD_TO_PDF"
    FILE_FIELD_NAME = "word_file"

    def get_serializer_class(self):
        return WordToPDFSerializer

    def get_docs_decorator(self):
        return word_to_pdf_docs

    def get_celery_task(self):
        """Get the Celery task function to execute."""
        return convert_word_to_pdf_task

    @word_to_pdf_docs()
    async def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        return await self.post_async(request)

    async def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform Word to PDF conversion."""
        docx_path, pdf_path = await convert_word_to_pdf(
            uploaded_file, suffix="_convertica"
        )
        return docx_path, pdf_path
