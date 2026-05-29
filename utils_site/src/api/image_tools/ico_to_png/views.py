# views.py
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from .decorators import ico_to_png_docs
from .serializers import ICOToPNGSerializer
from .utils import ico_to_png


class ICOToPNGAPIView(BaseConversionAPIView):
    """Convert a .ico file to PNG (extracting the largest embedded frame)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/x-icon",
        "image/vnd.microsoft.icon",
        "image/ico",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".ico"}
    CONVERSION_TYPE = "ico_to_png"
    FILE_FIELD_NAME = "ico_file"
    VALIDATE_PDF_PAGES = False

    def get_serializer_class(self):
        return ICOToPNGSerializer

    def get_docs_decorator(self):
        return ico_to_png_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET method not allowed. Use POST to convert an .ico file."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @ico_to_png_docs()
    def post(self, request: HttpRequest):
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        return ico_to_png(uploaded_file)

    def get_output_content_type(self, output_path: str) -> str:
        return "image/png"
