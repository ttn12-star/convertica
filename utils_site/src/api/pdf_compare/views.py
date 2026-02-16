"""API view for comparing two PDF files."""

import os
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from django.utils.text import get_valid_filename
from rest_framework import status
from rest_framework.response import Response

from ..base_views import BaseConversionAPIView
from ..premium_utils import is_premium_active
from .decorators import compare_pdf_docs
from .serializers import ComparePDFSerializer
from .utils import compare_pdf_files


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


class ComparePDFAPIView(BaseConversionAPIView):
    """Compare two PDFs and return visual diff package (premium only)."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "COMPARE_PDF"
    FILE_FIELD_NAME = "pdf_file_1"
    VALIDATE_PDF_PAGES = True

    def get_serializer_class(self):
        return ComparePDFSerializer

    def get_docs_decorator(self):
        return compare_pdf_docs

    @compare_pdf_docs()
    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        return super().post(request)

    def validate_file_additional(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        validated_data: dict,
    ) -> Response | None:
        comparison_file: UploadedFile | None = validated_data.get("pdf_file_2")
        if comparison_file is None:
            return Response(
                {"error": "pdf_file_2 is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comparison_context = {
            **context,
            "input_filename": comparison_file.name,
            "file_size": comparison_file.size,
        }
        validation_error = self.validate_file_basic(comparison_file, comparison_context)
        if validation_error is not None:
            return validation_error

        # Validate page limits for the second PDF as well.
        temp_dir = tempfile.mkdtemp(prefix="pdf_compare_validate_")
        try:
            temp_path = os.path.join(temp_dir, get_valid_filename(comparison_file.name))
            with open(temp_path, "wb") as temp_file:
                for chunk in comparison_file.chunks():
                    temp_file.write(chunk)
            comparison_file.seek(0)

            page_validation_error = self.validate_pdf_page_count(
                temp_path,
                comparison_context,
                user=getattr(self.request, "user", None),
                operation=self.CONVERSION_TYPE.lower(),
            )
            if page_validation_error is not None:
                return page_validation_error
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return None

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        comparison_file: UploadedFile = kwargs["pdf_file_2"]
        diff_threshold = kwargs.get("diff_threshold", 32)

        return compare_pdf_files(
            uploaded_file_1=uploaded_file,
            uploaded_file_2=comparison_file,
            diff_threshold=diff_threshold,
            suffix="_convertica",
        )

    def get_output_content_type(self, output_path: str) -> str:
        return "application/zip"
