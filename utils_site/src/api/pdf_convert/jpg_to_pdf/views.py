# views.py
import os

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...logging_utils import (
    build_request_context,
    get_logger,
    log_conversion_start,
    log_conversion_success,
    log_validation_error,
)
from .decorators import jpg_to_pdf_docs
from .serializers import JPGToPDFSerializer
from .utils import convert_jpg_to_pdf, convert_multiple_jpg_to_pdf

logger = get_logger(__name__)


class JPGToPDFAPIView(BaseConversionAPIView):
    """Handle JPG/JPEG → PDF conversion requests.

    Supports both single and multiple image files.
    Multiple images will be combined into a single PDF.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
    CONVERSION_TYPE = "JPG_TO_PDF"
    FILE_FIELD_NAME = "image_file"

    def get_serializer_class(self):
        return JPGToPDFSerializer

    def get_docs_decorator(self):
        return jpg_to_pdf_docs

    @jpg_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation.

        Supports multiple files - all images will be combined into one PDF.
        For multiple files, send multiple 'image_file' parameters in the form.
        """
        # Get all files with the same field name (supports multiple files)
        uploaded_files: list[UploadedFile] = request.FILES.getlist(self.FILE_FIELD_NAME)

        if not uploaded_files:
            context = build_request_context(request)
            return Response(
                {"error": f"{self.FILE_FIELD_NAME} is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate each file using serializer
        serializer_class = self.get_serializer_class()
        validation_errors = []

        for idx, uploaded_file in enumerate(uploaded_files):
            serializer = serializer_class(data={self.FILE_FIELD_NAME: uploaded_file})
            if not serializer.is_valid():
                validation_errors.append({f"file_{idx + 1}": serializer.errors})

        if validation_errors:
            context = build_request_context(request)
            log_validation_error(logger, {"files": validation_errors}, context)
            return Response(
                {"error": "File validation failed", "details": validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build context for logging
        context = build_request_context(request)
        context.update(
            {
                "num_files": len(uploaded_files),
                "total_size": sum(f.size for f in uploaded_files),
            }
        )

        # Validate all files (basic validation)
        for idx, uploaded_file in enumerate(uploaded_files):
            validation_error = self.validate_file_basic(uploaded_file, context)
            if validation_error:
                return validation_error

        tmp_dir = None
        start_time = None

        try:
            # Log conversion start
            start_time = log_conversion_start(logger, self.CONVERSION_TYPE, context)

            # Perform conversion (single or multiple)
            if len(uploaded_files) == 1:
                # Single file - use original function
                input_path, output_path = convert_jpg_to_pdf(
                    uploaded_files[0], suffix="_convertica"
                )
            else:
                # Multiple files - use new function
                input_path, output_path = convert_multiple_jpg_to_pdf(
                    uploaded_files, suffix="_convertica"
                )

            tmp_dir = os.path.dirname(input_path)

            # Stream file
            output_filename = os.path.basename(output_path)
            response = FileResponse(
                open(output_path, "rb"), as_attachment=True, filename=output_filename
            )
            response["Content-Type"] = self.get_output_content_type(output_path)

            # Log success
            log_conversion_success(
                logger,
                self.CONVERSION_TYPE,
                context,
                start_time,
                output_filename=output_filename,
                output_size_mb=round(os.path.getsize(output_path) / (1024 * 1024), 2),
            )

            return response

        except Exception as e:
            return self.handle_conversion_error(e, context, start_time)

        finally:
            self.cleanup_temp_files(tmp_dir, context)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform JPG to PDF conversion.

        This method is kept for compatibility but is not used in the new implementation.
        """
        image_path, pdf_path = convert_jpg_to_pdf(uploaded_file, suffix="_convertica")
        return image_path, pdf_path
