# views.py
import os
import time
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, FileResponse

from .serializers import CompressPDFSerializer
from .decorators import compress_pdf_docs
from .utils import compress_pdf
from ...base_views import BaseConversionAPIView
from ...logging_utils import build_request_context, get_logger, log_conversion_start, log_conversion_success


class CompressPDFAPIView(BaseConversionAPIView):
    """Handle compress PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "COMPRESS_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return CompressPDFSerializer

    def get_docs_decorator(self):
        return compress_pdf_docs

    @compress_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation and compression metadata."""
        from rest_framework.response import Response
        from rest_framework import status
        
        logger = get_logger(__name__)
        context = build_request_context(request)
        
        # Use the same logic as base class for data handling
        serializer_class = self.get_serializer_class()
        
        # Check if this is a DRF Request (has .data attribute)
        # DRF Request wraps Django's HttpRequest and provides request.data
        if hasattr(request, 'data') and request.data is not None:
            # DRF Request - request.data may be QueryDict or dict
            # DRF serializers can handle QueryDict directly, so pass it as-is
            serializer_data = request.data
        else:
            # Django HttpRequest - need to combine POST and FILES manually
            # Create a new QueryDict-like structure or use a regular dict
            from django.http import QueryDict
            # Combine POST and FILES into a single QueryDict
            # Start with POST data
            if request.POST:
                serializer_data = request.POST.copy()
            else:
                serializer_data = QueryDict(mutable=True)
            
            # Add files from FILES (they should override any string values with same key)
            if request.FILES:
                for key in request.FILES:
                    serializer_data[key] = request.FILES[key]
        
        # Log serializer data for debugging (excluding file content)
        try:
            data_keys = list(serializer_data.keys()) if hasattr(serializer_data, 'keys') else []
            file_keys = [k for k in data_keys if hasattr(serializer_data.get(k), 'read')]
            logger.debug("Serializer data keys: %s, file keys: %s", data_keys, file_keys, 
                        extra={"serializer_keys": data_keys, "file_keys": file_keys})
        except Exception:
            pass  # Ignore logging errors
        
        serializer = serializer_class(data=serializer_data)
        if not serializer.is_valid():
            logger.warning("Serializer validation failed: %s", serializer.errors, extra={
                **context, 
                "event": "validation_error",
                "errors": serializer.errors
            })
            return Response(
                {"error": "Invalid request", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_field_name = self.FILE_FIELD_NAME
        uploaded_file = serializer.validated_data.get(file_field_name)
        
        if not uploaded_file:
            return Response(
                {"error": "File is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Basic file validation
        validation_error = self.validate_file_basic(uploaded_file, context)
        if validation_error:
            return validation_error

        # Additional validation
        additional_validation_response = self.validate_file_additional(
            uploaded_file, context, serializer.validated_data
        )
        if additional_validation_response is not None:
            return additional_validation_response

        tmp_dir = None
        start_time = time.time()
        log_conversion_start(logger, self.CONVERSION_TYPE, context)

        try:
            # Perform conversion
            compression_level = serializer.validated_data.get('compression_level', 'medium')
            pdf_path, output_path = compress_pdf(
                uploaded_file,
                compression_level=compression_level,
                suffix="_convertica"
            )
            tmp_dir = os.path.dirname(pdf_path)
            
            # Calculate compression stats
            input_size = os.path.getsize(pdf_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
            
            # Stream file
            output_filename = os.path.basename(output_path)
            response = FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=output_filename
            )
            response["Content-Type"] = self.get_output_content_type(output_path)
            
            # Add compression metadata to response headers
            response["X-Input-Size"] = str(input_size)
            response["X-Output-Size"] = str(output_size)
            response["X-Compression-Ratio"] = f"{compression_ratio:.2f}"
            response["X-Compression-Level"] = compression_level
            
            # Log success
            log_conversion_success(
                logger,
                self.CONVERSION_TYPE,
                context,
                start_time,
                output_filename=output_filename,
                output_size_mb=round(output_size / (1024 * 1024), 2),
            )
            
            return response
        
        except Exception as e:
            return self.handle_conversion_error(e, context, start_time)
        
        finally:
            self.cleanup_temp_files(tmp_dir, context)

    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: dict,
        **kwargs
    ) -> Tuple[str, str]:
        """Compress PDF."""
        compression_level = kwargs.get('compression_level', 'medium')
        pdf_path, output_path = compress_pdf(
            uploaded_file,
            compression_level=compression_level,
            suffix="_convertica"
        )
        return pdf_path, output_path

