"""
Base API views for file conversion endpoints.
Reduces code duplication across conversion APIs.
"""
import os
import shutil
from typing import Optional, Callable, Tuple, Any, Dict
from abc import ABC, abstractmethod

from django.conf import settings
from django.http import FileResponse, HttpRequest
from django.utils.text import get_valid_filename
from django.core.files.uploadedfile import UploadedFile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from src.exceptions import (
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
    ConversionError,
)
from .logging_utils import (
    get_logger,
    build_request_context,
    log_conversion_start,
    log_conversion_success,
    log_conversion_error,
    log_validation_error,
    log_file_validation_error,
)

logger = get_logger(__name__)


class BaseConversionAPIView(APIView, ABC):
    """Base class for all file conversion API views.
    
    Provides common functionality:
    - File validation (size, type, extension)
    - Error handling
    - Logging
    - Temporary file cleanup
    """
    
    # Override these in subclasses
    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES: set = set()
    ALLOWED_EXTENSIONS: set = set()
    CONVERSION_TYPE = ""
    FILE_FIELD_NAME = "file"  # Override in serializer-specific views
    
    def get_serializer_class(self):
        """Get serializer class. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement get_serializer_class()")
    
    def get_docs_decorator(self) -> Callable:
        """Get Swagger docs decorator. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement get_docs_decorator()")
    
    @abstractmethod
    def perform_conversion(
        self,
        uploaded_file: UploadedFile,
        context: Dict[str, Any],
        **kwargs
    ) -> Tuple[str, str]:
        """Perform the actual conversion.
        
        Args:
            uploaded_file: The uploaded file to convert
            context: Logging context
            **kwargs: Additional conversion parameters
            
        Returns:
            Tuple[str, str]: (input_file_path, output_file_path)
            
        Raises:
            ConversionError, StorageError, InvalidPDFError, EncryptedPDFError
        """
        raise NotImplementedError("Subclasses must implement perform_conversion()")
    
    def get_output_content_type(self, output_path: str) -> str:
        """Get content type for output file. Override if needed."""
        # Default implementation - can be overridden
        ext = os.path.splitext(output_path)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def validate_file_basic(
        self,
        file: UploadedFile,
        context: Dict[str, Any]
    ) -> Optional[Response]:
        """Perform basic file validation.
        
        Returns:
            Response if validation failed, None if OK
        """
        # Check file is not empty
        if file.size == 0:
            log_file_validation_error(logger, "File is empty", context)
            return Response(
                {"error": "File is empty. Please upload a valid file."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check minimum file size
        if file.size < 100:
            log_file_validation_error(
                logger,
                f"File is too small: {file.size} bytes",
                context,
            )
            return Response(
                {"error": "File is too small to be valid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check maximum file size
        if file.size > self.MAX_UPLOAD_SIZE:
            log_file_validation_error(
                logger,
                f"File size {file.size} exceeds maximum {self.MAX_UPLOAD_SIZE}",
                context,
                max_size=self.MAX_UPLOAD_SIZE,
            )
            return Response(
                {"error": f"File too large. Maximum size is {self.MAX_UPLOAD_SIZE / (1024 * 1024):.0f} MB."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Check content type
        content_type = getattr(file, "content_type", None)
        if content_type and self.ALLOWED_CONTENT_TYPES and content_type not in self.ALLOWED_CONTENT_TYPES:
            log_file_validation_error(
                logger,
                f"Unsupported content type: {content_type}",
                context,
                content_type=content_type,
                allowed_types=list(self.ALLOWED_CONTENT_TYPES),
            )
            return Response(
                {"error": f"Unsupported content-type: {content_type}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check file extension
        safe_name = get_valid_filename(os.path.basename(file.name))
        _, ext = os.path.splitext(safe_name.lower())
        if self.ALLOWED_EXTENSIONS and ext not in self.ALLOWED_EXTENSIONS:
            log_file_validation_error(
                logger,
                f"Invalid file extension: {ext}",
                context,
                extension=ext,
                allowed_extensions=list(self.ALLOWED_EXTENSIONS),
            )
            return Response(
                {"error": f"Only {', '.join(self.ALLOWED_EXTENSIONS)} files are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return None
    
    def handle_conversion_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        start_time: Optional[float]
    ) -> Response:
        """Handle conversion errors with appropriate logging and response."""
        if isinstance(error, EncryptedPDFError):
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                context,
                error,
                start_time,
                level="warning",
            )
            return Response(
                {"error": "PDF is password-protected and cannot be converted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        elif isinstance(error, InvalidPDFError):
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                context,
                error,
                start_time,
                level="warning",
            )
            return Response(
                {"error": f"Invalid file: {str(error)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        elif isinstance(error, StorageError):
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                context,
                error,
                start_time,
                level="exception",
            )
            return Response(
                {"error": f"Internal storage error: {str(error)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        elif isinstance(error, ConversionError):
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                context,
                error,
                start_time,
                level="exception",
            )
            return Response(
                {"error": f"Conversion failed: {str(error)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        else:
            # Unexpected error
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                context,
                error,
                start_time,
                level="exception",
            )
            return Response(
                {"error": "Internal server error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def cleanup_temp_files(
        self,
        tmp_dir: Optional[str],
        context: Dict[str, Any]
    ):
        """Clean up temporary files."""
        if tmp_dir and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
                logger.debug(
                    "Temporary directory cleaned up",
                    extra={**context, "event": "cleanup", "tmp_dir": tmp_dir}
                )
            except Exception as cleanup_err:
                logger.exception(
                    "Failed to cleanup temp directory",
                    extra={
                        **context,
                        "event": "cleanup_error",
                        "tmp_dir": tmp_dir,
                        "error": str(cleanup_err),
                    }
                )
    
    def post(self, request: HttpRequest):
        """Handle POST request for file conversion.
        
        This is the main entry point that orchestrates:
        1. Serializer validation
        2. File validation
        3. Conversion
        4. Response
        5. Cleanup
        
        Note: Swagger documentation decorator should be applied in subclasses
        using @decorator() before this method.
        """
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.FILES or request.POST or request.data)
        
        if not serializer.is_valid():
            context = build_request_context(request)
            log_validation_error(logger, serializer.errors, context)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get file from serializer
        file_field_name = self.FILE_FIELD_NAME
        uploaded_file: Optional[UploadedFile] = serializer.validated_data.get(file_field_name)
        
        if uploaded_file is None:
            context = build_request_context(request)
            log_file_validation_error(
                logger,
                f"{file_field_name} field is missing",
                context
            )
            return Response(
                {"error": f"{file_field_name} is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build context for logging
        context = build_request_context(request, uploaded_file=uploaded_file)
        
        # Add any additional parameters from serializer to context
        for key, value in serializer.validated_data.items():
            if key != file_field_name:
                context[key] = value
        
        # Basic file validation
        validation_error = self.validate_file_basic(uploaded_file, context)
        if validation_error:
            return validation_error
        
        # Additional validation (can be overridden)
        additional_validation_response = self.validate_file_additional(
            uploaded_file, context, serializer.validated_data
        )
        if additional_validation_response is not None:
            return additional_validation_response
        
        tmp_dir = None
        start_time = None
        
        try:
            # Log conversion start
            start_time = log_conversion_start(logger, self.CONVERSION_TYPE, context)
            
            # Perform conversion
            input_path, output_path = self.perform_conversion(
                uploaded_file,
                context,
                **{k: v for k, v in serializer.validated_data.items() if k != file_field_name}
            )
            tmp_dir = os.path.dirname(input_path)
            
            # Stream file
            output_filename = os.path.basename(output_path)
            response = FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=output_filename
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
        
        except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError) as e:
            return self.handle_conversion_error(e, context, start_time)
        
        except Exception as e:
            return self.handle_conversion_error(e, context, start_time)
        
        finally:
            self.cleanup_temp_files(tmp_dir, context)
    
    def validate_file_additional(
        self,
        uploaded_file: UploadedFile,  # noqa: ARG002
        context: Dict[str, Any],  # noqa: ARG002
        validated_data: Dict[str, Any]  # noqa: ARG002
    ) -> Optional[Response]:
        """Override this method for additional file validation.
        
        Args:
            uploaded_file: The uploaded file
            context: Logging context
            validated_data: Validated serializer data
            
        Returns:
            Response if validation failed, None if OK
        """
        return None

