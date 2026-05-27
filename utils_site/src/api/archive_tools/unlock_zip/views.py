from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from ..protect_zip.views import ZIP_CONTENT_TYPES
from .decorators import unlock_zip_docs
from .serializers import UnlockZipSerializer
from .utils import unlock_zip


class UnlockZipAPIView(BaseConversionAPIView):
    """Handle Unlock ZIP requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = ZIP_CONTENT_TYPES
    ALLOWED_EXTENSIONS = {".zip"}
    CONVERSION_TYPE = "UNLOCK_ZIP"
    FILE_FIELD_NAME = "archive_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return UnlockZipSerializer

    def get_docs_decorator(self):
        return unlock_zip_docs

    @unlock_zip_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return unlock_zip(
            uploaded_file, password=kwargs.get("password", ""), suffix="_convertica"
        )
