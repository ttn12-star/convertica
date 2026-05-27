from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from ...base_views import BaseConversionAPIView
from .decorators import protect_zip_docs
from .serializers import ProtectZipSerializer
from .utils import protect_zip

ZIP_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
    "application/octet-stream",
}


class ProtectZipAPIView(BaseConversionAPIView):
    """Handle Protect ZIP requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = ZIP_CONTENT_TYPES
    ALLOWED_EXTENSIONS = {".zip"}
    CONVERSION_TYPE = "PROTECT_ZIP"
    FILE_FIELD_NAME = "archive_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ProtectZipSerializer

    def get_docs_decorator(self):
        return protect_zip_docs

    @protect_zip_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return protect_zip(
            uploaded_file, password=kwargs.get("password", ""), suffix="_convertica"
        )
