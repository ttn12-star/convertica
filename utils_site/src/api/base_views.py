"""
Base API views for file conversion endpoints.
Reduces code duplication across conversion APIs.
"""

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpRequest
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from .conversion_limits import (
    CONVERSION_TIMEOUT,
    MAX_PDF_PAGES,
    ConversionTimeoutError,
    get_timeout_for_operation,
    run_with_timeout,
    validate_pdf_pages,
)
from .file_validation import encode_filename_for_header, validate_output_file
from .logging_utils import (
    build_request_context,
    get_logger,
    log_conversion_error,
    log_conversion_start,
    log_conversion_success,
    log_file_validation_error,
    log_validation_error,
)
from .rate_limit_utils import combined_rate_limit
from .spam_protection import validate_spam_protection

logger = get_logger(__name__)


class BaseConversionAPIView(APIView, ABC):
    """Base class for all file conversion API views.

    Provides common functionality:
    - File validation (size, type, extension)
    - PDF page limit validation
    - Conversion timeout protection
    - Error handling
    - Logging
    - Temporary file cleanup
    """

    # Override these in subclasses
    MAX_UPLOAD_SIZE = getattr(
        settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024
    )  # Default for backwards compatibility
    ALLOWED_CONTENT_TYPES: set = set()
    ALLOWED_EXTENSIONS: set = set()
    CONVERSION_TYPE = ""

    def get_max_file_size(self, request) -> int:
        """Get maximum file size for user based on premium status.

        Args:
            request: HTTP request with user info

        Returns:
            Maximum file size in bytes
        """
        from .conversion_limits import get_max_file_size_for_user

        if hasattr(request, "user") and request.user:
            return get_max_file_size_for_user(request.user, self.CONVERSION_TYPE)
        return self.MAX_UPLOAD_SIZE

    FILE_FIELD_NAME = "file"  # Override in serializer-specific views

    # PDF page limit (override in subclasses if needed)
    MAX_PDF_PAGES = MAX_PDF_PAGES  # Default from conversion_limits

    # Conversion timeout in seconds (override for heavy operations)
    CONVERSION_TIMEOUT = CONVERSION_TIMEOUT

    # Whether this operation requires PDF page validation
    VALIDATE_PDF_PAGES = True  # Set to False for non-PDF operations

    # Whether file upload is required (False for URL/HTML conversions)
    FILE_FIELD_REQUIRED = True

    def get_serializer_class(self):
        """Get serializer class. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement get_serializer_class()")

    def get_docs_decorator(self) -> Callable:
        """Get Swagger docs decorator. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement get_docs_decorator()")

    @abstractmethod
    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict[str, Any], **kwargs
    ) -> tuple[str, str]:
        """Perform the actual conversion.

        Args:
            uploaded_file: The uploaded file to convert
            context: Logging context
            **kwargs: Additional conversion parameters

        Returns:
            Tuple[str, str]: (input_file_path, output_file_path)

        Can be either sync or async method - subclasses can override as async if needed.
        """
        raise NotImplementedError("Subclasses must implement perform_conversion()")

    def get_output_content_type(self, output_path: str) -> str:
        """Get content type for output file. Override if needed."""
        # Default implementation - can be overridden
        ext = os.path.splitext(output_path)[1].lower()
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".html": "text/html; charset=utf-8",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".zip": "application/zip",
        }
        return content_types.get(ext, "application/octet-stream")

    def validate_file_basic(
        self, file: UploadedFile, context: dict[str, Any]
    ) -> Response | None:
        """Perform basic file validation.

        Returns:
            Response if validation failed, None if OK
        """
        # Check file is not empty
        if file.size == 0:
            log_file_validation_error(logger, "File is empty", context)
            return Response(
                {"error": _("File is empty. Please upload a valid file.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check minimum file size
        if file.size < 100:
            log_file_validation_error(
                logger,
                f"File is too small: {file.size} bytes",
                context,
            )
            return Response(
                {"error": _("File is too small to be valid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request = context.get("request") or getattr(self, "request", None)

        # Check maximum file size (dynamic based on user premium status)
        max_file_size = self.get_max_file_size(request)
        if file.size > max_file_size:
            log_file_validation_error(
                logger,
                f"File size {file.size} exceeds maximum {max_file_size}",
                context,
                max_size=max_file_size,
            )

            # Check if user is premium for custom message
            from .premium_utils import is_premium_active

            is_premium = is_premium_active(
                request.user if hasattr(request, "user") else None
            )

            free_limit = settings.MAX_FILE_SIZE_FREE
            premium_limit = settings.MAX_FILE_SIZE_PREMIUM

            if not is_premium and file.size > free_limit:
                # Free user exceeding limit - offer upgrade
                return Response(
                    {
                        "error": _(
                            "File too large (%(file_mb).1f MB). Free users: max %(free_mb).0f MB. "
                            "Upgrade to Premium for %(premium_mb).0f MB limit."
                        )
                        % {
                            "file_mb": file.size / (1024 * 1024),
                            "free_mb": free_limit / (1024 * 1024),
                            "premium_mb": premium_limit / (1024 * 1024),
                        }
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
            else:
                return Response(
                    {
                        "error": _("File too large. Maximum size is %(max_mb).0f MB.")
                        % {"max_mb": max_file_size / (1024 * 1024)}
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

        # Check content type
        content_type = getattr(file, "content_type", None)
        if (
            content_type
            and self.ALLOWED_CONTENT_TYPES
            and content_type not in self.ALLOWED_CONTENT_TYPES
        ):
            log_file_validation_error(
                logger,
                f"Unsupported content type: {content_type}",
                context,
                content_type=content_type,
                allowed_types=list(self.ALLOWED_CONTENT_TYPES),
            )
            return Response(
                {
                    "error": _("Unsupported content-type: %(content_type)s")
                    % {"content_type": content_type}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check file extension
        safe_name = get_valid_filename(os.path.basename(file.name))
        _base, ext = os.path.splitext(safe_name.lower())
        if self.ALLOWED_EXTENSIONS and ext not in self.ALLOWED_EXTENSIONS:
            log_file_validation_error(
                logger,
                f"Invalid file extension: {ext}",
                context,
                extension=ext,
                allowed_extensions=list(self.ALLOWED_EXTENSIONS),
            )
            return Response(
                {
                    "error": _("Only %(extensions)s files are allowed.")
                    % {"extensions": ", ".join(self.ALLOWED_EXTENSIONS)}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    def handle_conversion_error(
        self, error: Exception, context: dict[str, Any], start_time: float | None
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
            # Use the original error message so users understand the exact problem
            # (e.g. incorrect password, empty password), while keeping 400 status.
            message = (
                str(error).strip()
                or "PDF is password-protected and cannot be converted."
            )
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elif isinstance(error, InvalidPDFError):
            # Mark as handled error in Sentry (expected user error, not bug)
            try:
                import sentry_sdk

                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("error_type", "handled")
                    scope.set_tag("user_error", "true")
                    scope.set_tag("conversion_type", self.CONVERSION_TYPE)
                    scope.level = "info"  # Lower severity since it's handled
            except (ImportError, Exception):
                pass  # Sentry not available or failed

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
                status=status.HTTP_400_BAD_REQUEST,
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def cleanup_temp_files(self, tmp_dir: str | None, context: dict[str, Any]):
        """Clean up temporary files."""
        if tmp_dir and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
                logger.debug(
                    "Temporary directory cleaned up",
                    extra={**context, "event": "cleanup", "tmp_dir": tmp_dir},
                )
            except Exception as cleanup_err:
                logger.exception(
                    "Failed to cleanup temp directory",
                    extra={
                        **context,
                        "event": "cleanup_error",
                        "tmp_dir": tmp_dir,
                        "error": str(cleanup_err),
                    },
                )

    async def post_async(self, request: HttpRequest):
        """Async version of post method for optimized converters.

        This method supports async perform_conversion methods.
        Subclasses that use async conversion should override post() to call this method.
        """
        # Spam protection check
        spam_check = validate_spam_protection(request)
        if spam_check:
            return spam_check

        serializer_class = self.get_serializer_class()
        # Combine all data sources: request.data (DRF), request.POST, and request.FILES
        if hasattr(request, "data") and request.data is not None:
            serializer_data = request.data
        else:
            from django.http import QueryDict

            if request.POST:
                serializer_data = request.POST.copy()
            else:
                serializer_data = QueryDict(mutable=True)
            if request.FILES:
                for key in request.FILES:
                    serializer_data[key] = request.FILES[key]

        # Validate serializer
        serializer = serializer_class(data=serializer_data)
        if not serializer.is_valid():
            context = build_request_context(request)
            log_validation_error(logger, serializer.errors, context)
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get uploaded file
        uploaded_file = serializer.validated_data[self.FILE_FIELD_NAME]

        # IMPORTANT: don't use reserved LogRecord keys (e.g. "filename") in logging extra.
        # build_request_context already includes safe keys like uploaded_filename.
        context = build_request_context(request, uploaded_file=uploaded_file)

        # Validate file
        validation_error = self.validate_file_basic(uploaded_file, context)
        if validation_error:
            return validation_error

        # Additional validation
        additional_validation = self.validate_file_additional(
            uploaded_file, context, serializer.validated_data
        )
        if additional_validation:
            return additional_validation

        # Page validation for PDF files
        if self.VALIDATE_PDF_PAGES and self._is_pdf_file(uploaded_file):
            validation_tmp_dir = tempfile.mkdtemp(prefix="pdf_validate_")
            try:
                temp_pdf_path = os.path.join(
                    validation_tmp_dir,
                    get_valid_filename(uploaded_file.name),
                )
                with open(temp_pdf_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                uploaded_file.seek(0)

                operation = getattr(self, "CONVERSION_TYPE", "").lower()
                page_validation_error = self.validate_pdf_page_count(
                    temp_pdf_path, context, user=request.user, operation=operation
                )
                if page_validation_error is not None:
                    return page_validation_error
            finally:
                shutil.rmtree(validation_tmp_dir, ignore_errors=True)

        tmp_dir = None
        start_time = None
        op_run_id = None

        try:
            # Log conversion start
            start_time = log_conversion_start(logger, self.CONVERSION_TYPE, context)

            # Lightweight DB analytics (best-effort)
            try:
                from django.utils import timezone
                from src.users.models import OperationRun

                op_run_id = str(context.get("request_id") or uuid.uuid4().hex)
                context["operation_run_id"] = op_run_id

                is_premium = bool(
                    request.user.is_authenticated
                    and getattr(request.user, "is_premium", False)
                    and (
                        request.user.is_subscription_active()
                        if callable(
                            getattr(request.user, "is_subscription_active", None)
                        )
                        else bool(
                            getattr(request.user, "is_subscription_active", False)
                        )
                    )
                )

                OperationRun.objects.update_or_create(
                    request_id=op_run_id,
                    defaults={
                        "conversion_type": self.CONVERSION_TYPE,
                        "status": "running",
                        "user": request.user if request.user.is_authenticated else None,
                        "is_premium": is_premium,
                        "input_size": context.get("file_size"),
                        "started_at": timezone.now(),
                        "remote_addr": str(context.get("remote_addr") or ""),
                        "user_agent": str(context.get("user_agent") or ""),
                        "path": str(context.get("path") or ""),
                    },
                )
            except Exception:
                op_run_id = None

            # Get timeout for this operation
            timeout = self.get_conversion_timeout(context)
            context["conversion_timeout"] = timeout

            # Perform async conversion with timeout
            try:
                input_path, output_path = await asyncio.wait_for(
                    self.perform_conversion(
                        uploaded_file, context, **serializer.validated_data
                    ),
                    timeout=timeout,
                )
            except TimeoutError:
                raise ConversionTimeoutError(
                    f"Conversion timed out after {timeout} seconds", context=context
                )

            # Validate output
            validate_output_file(output_path, context=context)

            # Stream file
            output_filename = os.path.basename(output_path)
            response = FileResponse(open(output_path, "rb"))
            response["Content-Disposition"] = encode_filename_for_header(
                output_filename
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

            # Update analytics (best-effort)
            if op_run_id:
                try:
                    from django.utils import timezone
                    from src.users.models import OperationRun

                    now = timezone.now()
                    duration_ms = None
                    if start_time:
                        duration_ms = int((time.time() - start_time) * 1000)
                    OperationRun.objects.filter(request_id=op_run_id).update(
                        status="success",
                        finished_at=now,
                        duration_ms=duration_ms,
                        output_size=os.path.getsize(output_path),
                    )
                except Exception:
                    pass

            return response

        except Exception as e:
            if op_run_id:
                try:
                    from django.utils import timezone
                    from src.users.models import OperationRun

                    now = timezone.now()
                    duration_ms = None
                    if start_time:
                        duration_ms = int((time.time() - start_time) * 1000)
                    OperationRun.objects.filter(request_id=op_run_id).update(
                        status="error",
                        finished_at=now,
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e)[:2000],
                    )
                except Exception:
                    pass
            return self.handle_conversion_error(e, context, start_time)

        finally:
            # Cleanup temporary directory
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    @combined_rate_limit(group="api_conversion", ip_rate="100/h", methods=["POST"])
    def post(self, request: HttpRequest):
        """Handle POST request for file conversion.

        This is the main entry point that orchestrates:
        1. Spam protection
        2. Serializer validation
        3. File validation
        4. Conversion
        5. Response
        6. Cleanup

        Note: Swagger documentation decorator should be applied in subclasses
        using @decorator() before this method.

        Rate limits:
        - IP: 100 requests/hour (prevents IP-based abuse)
        - Anonymous: 100 requests/hour
        - Authenticated: 1,000 requests/hour
        - Premium: 10,000 requests/hour
        """
        # Spam protection check
        spam_check = validate_spam_protection(request)
        if spam_check:
            return spam_check

        serializer_class = self.get_serializer_class()
        # Combine all data sources: request.data (DRF), request.POST, and request.FILES
        # This ensures form-data parameters are properly passed to the serializer
        # DRF serializers can work with QueryDict directly, so we try to preserve it when possible

        # Check if this is a DRF Request (has .data attribute)
        # DRF Request wraps Django's HttpRequest and provides request.data
        if hasattr(request, "data") and request.data is not None:
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
            data_keys = list(serializer_data.keys())
            file_keys = [
                k for k in data_keys if hasattr(serializer_data.get(k), "read")
            ]
            logger.debug(
                f"Serializer data keys: {data_keys}, file keys: {file_keys}",
                extra={"serializer_keys": data_keys, "file_keys": file_keys},
            )
        except Exception:
            pass  # Ignore logging errors

        serializer = serializer_class(data=serializer_data)

        if not serializer.is_valid():
            context = build_request_context(request)
            # Log detailed validation errors
            error_details = dict(serializer.errors)
            logger.warning(
                f"Validation errors: {error_details}",
                extra={**context, "validation_errors": error_details},
            )
            log_validation_error(logger, serializer.errors, context)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get file from serializer
        file_field_name = self.FILE_FIELD_NAME
        uploaded_file: UploadedFile | None = serializer.validated_data.get(
            file_field_name
        )

        # Check if file is required (some conversions like URL to PDF don't need file upload)
        if uploaded_file is None and self.FILE_FIELD_REQUIRED:
            context = build_request_context(request)
            log_file_validation_error(
                logger, f"{file_field_name} field is missing", context
            )
            return Response(
                {"error": f"{file_field_name} is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build context for logging
        context = build_request_context(request, uploaded_file=uploaded_file)

        # Add request to context for converters that need it (URL/HTML)
        context["request"] = request

        # Add any additional parameters from serializer to context
        # Rename keys that conflict with LogRecord attributes
        reserved_keys = {
            "filename",
            "funcName",
            "levelname",
            "lineno",
            "module",
            "msecs",
            "name",
            "pathname",
            "process",
            "processName",
        }
        for key, value in serializer.validated_data.items():
            if key != file_field_name:
                # Rename reserved keys to avoid LogRecord conflicts
                if key in reserved_keys:
                    context[f"input_{key}"] = value
                else:
                    context[key] = value

        # OCR validation for premium users
        if context.get("ocr_enabled", False):
            from django.conf import settings

            payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)

            if not request.user.is_authenticated:
                logger.warning(
                    "OCR requested by unauthenticated user",
                    extra={**context, "event": "ocr_unauthorized"},
                )
                if payments_enabled:
                    error_msg = "OCR is a premium feature. Please log in and upgrade to Premium."
                else:
                    error_msg = "OCR feature is not available. Please log in to use this feature."
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_403_FORBIDDEN,
                )
            elif not getattr(request.user, "is_premium", False) or not (
                request.user.is_subscription_active()
                if callable(getattr(request.user, "is_subscription_active", None))
                else bool(getattr(request.user, "is_subscription_active", False))
            ):
                logger.warning(
                    "OCR requested by non-premium user",
                    extra={**context, "event": "ocr_non_premium"},
                )
                if payments_enabled:
                    error_msg = "OCR is a premium feature. Upgrade to Premium to enable OCR processing."
                else:
                    error_msg = "OCR feature is not available at this time."
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Basic file validation (skip if no file uploaded - for URL/HTML conversions)
        if uploaded_file is not None:
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
        op_run_id = None
        validation_tmp_dir = None

        try:
            # For PDF operations, validate page count before conversion
            if self.VALIDATE_PDF_PAGES and self._is_pdf_file(uploaded_file):
                # Save file temporarily to validate page count
                validation_tmp_dir = tempfile.mkdtemp(prefix="pdf_validate_")
                temp_pdf_path = os.path.join(
                    validation_tmp_dir,
                    get_valid_filename(uploaded_file.name),
                )
                with open(temp_pdf_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                # Reset file pointer for later use
                uploaded_file.seek(0)

                # Validate page count with user context
                operation = getattr(self, "CONVERSION_TYPE", "").lower()
                page_validation_error = self.validate_pdf_page_count(
                    temp_pdf_path, context, user=request.user, operation=operation
                )
                if page_validation_error is not None:
                    logger.info(
                        f"Returning page validation error: {page_validation_error.data}"
                    )
                    return page_validation_error

                # Cleanup validation temp dir
                shutil.rmtree(validation_tmp_dir, ignore_errors=True)
                validation_tmp_dir = None

            # Log conversion start
            start_time = log_conversion_start(logger, self.CONVERSION_TYPE, context)

            # Get timeout for this operation
            timeout = self.get_conversion_timeout(context)
            context["conversion_timeout"] = timeout

            logger.debug(
                "Starting conversion with timeout",
                extra={**context, "timeout_seconds": timeout},
            )

            # Create Sentry transaction for performance tracking
            try:
                import sentry_sdk

                transaction = sentry_sdk.start_transaction(
                    op="conversion",
                    name=f"{self.CONVERSION_TYPE} conversion",
                )
                transaction.set_tag("conversion_type", self.CONVERSION_TYPE)
                transaction.set_data("file_size_mb", context.get("file_size_mb", 0))
            except (ImportError, Exception):
                transaction = None

            # Perform conversion WITH TIMEOUT
            try:
                if transaction:
                    with transaction:
                        input_path, output_path = run_with_timeout(
                            self.perform_conversion,
                            args=(uploaded_file, context),
                            kwargs={
                                k: v
                                for k, v in serializer.validated_data.items()
                                if k != file_field_name
                            },
                            timeout=timeout,
                        )
                else:
                    input_path, output_path = run_with_timeout(
                        self.perform_conversion,
                        args=(uploaded_file, context),
                        kwargs={
                            k: v
                            for k, v in serializer.validated_data.items()
                            if k != file_field_name
                        },
                        timeout=timeout,
                    )
            except ConversionTimeoutError as timeout_err:
                log_conversion_error(
                    logger,
                    self.CONVERSION_TYPE,
                    context,
                    timeout_err,
                    start_time,
                    level="warning",
                )
                return Response(
                    {
                        "error": str(timeout_err),
                        "hint": "Try with a smaller file or fewer pages.",
                    },
                    status=status.HTTP_408_REQUEST_TIMEOUT,
                )

            tmp_dir = os.path.dirname(input_path)

            # Stream file
            output_filename = os.path.basename(output_path)
            response = FileResponse(open(output_path, "rb"))
            response["Content-Disposition"] = encode_filename_for_header(
                output_filename
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
            if op_run_id:
                try:
                    from django.utils import timezone
                    from src.users.models import OperationRun

                    now = timezone.now()
                    duration_ms = None
                    if start_time:
                        duration_ms = int((time.time() - start_time) * 1000)
                    OperationRun.objects.filter(request_id=op_run_id).update(
                        status="error",
                        finished_at=now,
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e)[:2000],
                    )
                except Exception:
                    pass
            return self.handle_conversion_error(e, context, start_time)

        except Exception as e:
            if op_run_id:
                try:
                    from django.utils import timezone
                    from src.users.models import OperationRun

                    now = timezone.now()
                    duration_ms = None
                    if start_time:
                        duration_ms = int((time.time() - start_time) * 1000)
                    OperationRun.objects.filter(request_id=op_run_id).update(
                        status="error",
                        finished_at=now,
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e)[:2000],
                    )
                except Exception:
                    pass
            return self.handle_conversion_error(e, context, start_time)

        finally:
            self.cleanup_temp_files(tmp_dir, context)
            if validation_tmp_dir:
                shutil.rmtree(validation_tmp_dir, ignore_errors=True)

    def _is_pdf_file(self, uploaded_file: UploadedFile) -> bool:
        """Check if the uploaded file is a PDF."""
        name = getattr(uploaded_file, "name", "") or ""
        content_type = getattr(uploaded_file, "content_type", "") or ""
        return name.lower().endswith(".pdf") or "pdf" in content_type.lower()

    def validate_file_additional(
        self,
        uploaded_file: UploadedFile,  # noqa: ARG002
        context: dict[str, Any],  # noqa: ARG002
        validated_data: dict[str, Any],  # noqa: ARG002
    ) -> Response | None:
        """Override this method for additional file validation.

        Args:
            uploaded_file: The uploaded file
            context: Logging context
            validated_data: Validated serializer data

        Returns:
            Response if validation failed, None if OK
        """
        return None

    def validate_pdf_page_count(
        self, pdf_path: str, context: dict[str, Any], user=None, operation: str = None
    ) -> Response | None:
        """Validate PDF page count doesn't exceed limit.

        Args:
            pdf_path: Path to the PDF file
            context: Logging context
            user: Django user object (optional)
            operation: Type of operation (optional)

        Returns:
            Response if validation failed, None if OK
        """
        if not self.VALIDATE_PDF_PAGES:
            return None

        is_valid, error_message, page_count = validate_pdf_pages(
            pdf_path, self.MAX_PDF_PAGES, user=user, operation=operation
        )

        context["pdf_page_count"] = page_count

        if not is_valid:
            log_file_validation_error(
                logger,
                f"PDF page limit exceeded: {page_count} > {self.MAX_PDF_PAGES}",
                context,
            )
            # Add premium upgrade link for free users
            response_data = {"error": error_message}
            payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)

            # Show upgrade link if payments enabled and user is not premium
            # (either not authenticated or authenticated but not premium)
            if payments_enabled and (
                not user
                or not user.is_authenticated
                or not getattr(user, "is_premium", False)
            ):
                try:
                    response_data["upgrade_url"] = reverse("frontend:pricing")
                except Exception:
                    response_data["upgrade_url"] = "/pricing/"
                response_data["upgrade_text"] = "Upgrade to Premium"

            return Response(
                response_data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    def get_conversion_timeout(self, context: dict[str, Any]) -> int:
        """Get timeout for this conversion.

        Override in subclasses for custom timeout logic.

        Args:
            context: Logging context (may contain page_count, file_size)

        Returns:
            Timeout in seconds
        """
        page_count = context.get("pdf_page_count", 1)
        file_size = context.get("file_size", 0)

        return get_timeout_for_operation(
            self.CONVERSION_TYPE,
            page_count=page_count,
            file_size=file_size,
        )
