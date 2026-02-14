"""
Async API views for heavy conversion operations.

These views handle file conversions asynchronously via Celery to avoid
Cloudflare timeout issues (100 seconds limit).

Flow:
1. POST /api/{conversion}/ - Upload file, start Celery task, return task_id immediately
2. GET /api/tasks/{task_id}/status/ - Check task status and progress
3. GET /api/tasks/{task_id}/result/ - Download result when ready

Storage: Uses MEDIA_ROOT/async_temp/ for temporary files - this directory
is shared between web and celery containers via volume mount.
"""

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from typing import Any

from celery.result import AsyncResult
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpRequest
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .conversion_limits import (
    HEAVY_OPERATIONS,
    MAX_PDF_PAGES,
    MAX_PDF_PAGES_HEAVY,
    validate_file_for_operation,
    validate_pdf_pages,
)
from .logging_utils import build_request_context, get_logger, log_file_validation_error
from .operation_run_middleware_utils import ensure_request_id
from .spam_protection import validate_spam_protection
from .task_tokens import create_task_token, verify_task_token

logger = get_logger(__name__)

# Directory for storing files during async processing
# Uses MEDIA_ROOT to ensure shared access between web and celery containers
_media_root = getattr(settings, "MEDIA_ROOT", None)
if _media_root is None:
    _media_root = "/app/media"
else:
    _media_root = str(_media_root)  # Convert Path to string if needed

ASYNC_TEMP_DIR = getattr(
    settings,
    "ASYNC_TEMP_DIR",
    os.path.join(_media_root, "async_temp"),
)

# How long to keep temp files (seconds) - cleaned by maintenance task
ASYNC_TEMP_FILE_TTL = getattr(settings, "ASYNC_TEMP_FILE_TTL", 3600)  # 1 hour


def get_task_temp_dir(task_id: str) -> str:
    """Get temporary directory for a specific task."""
    task_dir = os.path.join(ASYNC_TEMP_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def cleanup_task_files(task_id: str):
    """Clean up temporary files for a task."""
    task_dir = os.path.join(ASYNC_TEMP_DIR, task_id)
    if os.path.isdir(task_dir):
        try:
            shutil.rmtree(task_dir)
            logger.debug(f"Cleaned up task files: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup task files {task_id}: {e}")


def _extract_task_token(request: HttpRequest) -> str | None:
    """Extract task token from query params or request headers."""
    return request.GET.get("task_token") or request.headers.get("X-Task-Token")


def _authorize_task_request(
    request: HttpRequest, task_id: str, task_token: str | None
) -> bool:
    """Authorize task access by token or ownership (no IP fallback)."""
    user = getattr(request, "user", None)

    if user is not None and getattr(user, "is_authenticated", False):
        if task_token and (
            verify_task_token(task_token, task_id, user.id)
            or verify_task_token(task_token, task_id, None)
        ):
            return True
        try:
            from src.users.models import OperationRun

            return OperationRun.objects.filter(task_id=task_id, user=user).exists()
        except Exception:
            return False

    return bool(task_token and verify_task_token(task_token, task_id, None))


class AsyncConversionAPIView(APIView, ABC):
    """Base class for async file conversion API views.

    Provides async conversion flow:
    1. Accept file upload
    2. Save to temp storage
    3. Create Celery task
    4. Return task_id immediately (fast response, no timeout!)

    Subclasses must implement:
    - get_celery_task(): Return the Celery task function
    - get_task_kwargs(): Return additional kwargs for the task
    """

    # Override these in subclasses
    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES: set = set()
    ALLOWED_EXTENSIONS: set = set()
    CONVERSION_TYPE = ""
    FILE_FIELD_NAME = "file"

    # PDF page limit (override in subclasses if needed)
    MAX_PDF_PAGES = MAX_PDF_PAGES

    # Whether this operation requires PDF page validation
    VALIDATE_PDF_PAGES = True

    @abstractmethod
    def get_serializer_class(self):
        """Get serializer class. Override in subclasses."""
        raise NotImplementedError()

    @abstractmethod
    def get_celery_task(self):
        """Get the Celery task function to execute."""
        raise NotImplementedError()

    def get_task_kwargs(self, validated_data: dict) -> dict:
        """Get additional kwargs for the Celery task.

        Override in subclasses to pass extra parameters.
        """
        return {}

    def _is_premium_active(self, request: HttpRequest) -> bool:
        """Check whether request user has active premium subscription."""
        return (
            request.user.is_authenticated
            and getattr(request.user, "is_premium", False)
            and request.user.is_subscription_active()
        )

    def get_max_file_size(self, request: HttpRequest) -> int:
        """Get max file size dynamically based on user and conversion type."""
        from .conversion_limits import get_max_file_size_for_user

        return get_max_file_size_for_user(request.user, self.CONVERSION_TYPE)

    def _is_json_serializable(self, obj) -> bool:
        """Check if object is JSON serializable."""
        try:
            import json

            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

    def validate_file_basic(
        self, file: UploadedFile, context: dict[str, Any]
    ) -> Response | None:
        """Perform basic file validation."""
        # Check file is not empty
        if file.size == 0:
            log_file_validation_error(logger, "File is empty", context)
            return Response(
                {"error": "File is empty. Please upload a valid file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check minimum file size
        if file.size < 100:
            log_file_validation_error(
                logger, f"File is too small: {file.size} bytes", context
            )
            return Response(
                {"error": "File is too small to be valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check maximum file size (dynamic based on user premium status)
        request = getattr(self, "request", None)
        max_file_size = self.MAX_UPLOAD_SIZE
        if request is not None:
            max_file_size = self.get_max_file_size(request)

        if file.size > max_file_size:
            log_file_validation_error(
                logger,
                f"File size {file.size} exceeds maximum {max_file_size}",
                context,
            )
            payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
            if (
                request is not None
                and not self._is_premium_active(request)
                and payments_enabled
            ):
                response_data = {
                    "error": gettext(
                        "File too large (%(file_mb).1f MB). Free users: max %(free_mb).0f MB. "
                        "Upgrade to Premium for %(premium_mb).0f MB limit! "
                        "Get 1-day Premium for just $1."
                    )
                    % {
                        "file_mb": file.size / (1024 * 1024),
                        "free_mb": getattr(
                            settings, "MAX_FILE_SIZE_FREE", max_file_size
                        )
                        / (1024 * 1024),
                        "premium_mb": max_file_size / (1024 * 1024),
                    },
                }
                try:
                    response_data["upgrade_url"] = reverse("frontend:pricing")
                except Exception:
                    response_data["upgrade_url"] = "/pricing/"
                response_data["upgrade_text"] = gettext("Upgrade to Premium")
                return Response(
                    response_data,
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
            return Response(
                {
                    "error": gettext("File too large. Maximum size is %(max_mb).0f MB.")
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
                logger, f"Unsupported content type: {content_type}", context
            )
            return Response(
                {"error": f"Unsupported content-type: {content_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check file extension
        safe_name = get_valid_filename(os.path.basename(file.name))
        _, ext = os.path.splitext(safe_name.lower())
        if self.ALLOWED_EXTENSIONS and ext not in self.ALLOWED_EXTENSIONS:
            log_file_validation_error(logger, f"Invalid file extension: {ext}", context)
            return Response(
                {
                    "error": f"Only {', '.join(self.ALLOWED_EXTENSIONS)} files are allowed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    def _is_pdf_file(self, uploaded_file: UploadedFile) -> bool:
        """Check if the uploaded file is a PDF."""
        name = getattr(uploaded_file, "name", "") or ""
        content_type = getattr(uploaded_file, "content_type", "") or ""
        return name.lower().endswith(".pdf") or "pdf" in content_type.lower()

    def post(self, request: HttpRequest):
        """Handle POST request - start async conversion.

        Returns task_id immediately for polling.
        """
        # Spam protection
        spam_check = validate_spam_protection(request)
        if spam_check:
            return spam_check

        # Validate with serializer
        serializer_class = self.get_serializer_class()
        serializer_data = request.data if hasattr(request, "data") else request.POST
        serializer = serializer_class(data=serializer_data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get uploaded file
        uploaded_file: UploadedFile | None = serializer.validated_data.get(
            self.FILE_FIELD_NAME
        )
        if not uploaded_file:
            return Response(
                {"error": f"{self.FILE_FIELD_NAME} is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build context
        ensure_request_id(request)
        context = build_request_context(request, uploaded_file=uploaded_file)

        # Basic validation
        validation_error = self.validate_file_basic(uploaded_file, context)
        if validation_error:
            return validation_error

        # Generate unique task ID
        task_id = str(uuid.uuid4())
        task_dir = get_task_temp_dir(task_id)

        # Lightweight DB analytics for async queueing (best-effort)
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            is_premium = self._is_premium_active(request)

            OperationRun.objects.update_or_create(
                request_id=str(context.get("request_id") or ""),
                defaults={
                    "conversion_type": self.CONVERSION_TYPE,
                    "status": "queued",
                    "user": request.user if request.user.is_authenticated else None,
                    "is_premium": bool(is_premium),
                    "task_id": task_id,
                    "input_size": getattr(uploaded_file, "size", None),
                    "queued_at": timezone.now(),
                    "remote_addr": str(context.get("remote_addr") or ""),
                    "user_agent": str(context.get("user_agent") or ""),
                    "path": str(context.get("path") or ""),
                },
            )
        except Exception:
            pass

        try:
            # Save uploaded file using async file operations
            file_extension = os.path.splitext(uploaded_file.name)[1]
            input_path = os.path.join(task_dir, f"input_{task_id}{file_extension}")

            try:
                # Use sync file saving to avoid event loop issues in Django view context
                with open(input_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                # Verify file was saved successfully
                if not os.path.exists(input_path):
                    raise OSError(f"Failed to save file: {input_path}")

                file_size = os.path.getsize(input_path)
                logger.info(
                    f"File saved successfully: {input_path} ({file_size} bytes)",
                    extra=context,
                )

            except OSError as e:
                cleanup_task_files(task_id)
                raise ValidationError(
                    f"Failed to save uploaded file: {e}",
                    context={**context, "error": str(e)},
                )

            # Validate PDF pages if needed
            if self.VALIDATE_PDF_PAGES and self._is_pdf_file(uploaded_file):
                # Use stricter limits for heavy operations
                max_pages = (
                    MAX_PDF_PAGES_HEAVY
                    if self.CONVERSION_TYPE in HEAVY_OPERATIONS
                    else self.MAX_PDF_PAGES
                )
                is_valid, error_message, page_count = validate_pdf_pages(
                    input_path,
                    max_pages,
                    user=request.user,
                    operation=self.CONVERSION_TYPE,
                )
                if not is_valid:
                    cleanup_task_files(task_id)
                    response_data = {
                        "error": error_message,
                        "page_count": page_count,
                        "max_pages": max_pages,
                    }
                    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
                    if payments_enabled and not self._is_premium_active(request):
                        try:
                            response_data["upgrade_url"] = reverse("frontend:pricing")
                        except Exception:
                            response_data["upgrade_url"] = "/pricing/"
                        response_data["upgrade_text"] = gettext("Upgrade to Premium")
                    return Response(
                        response_data,
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # For heavy operations, do additional validation (complexity, size)
                if self.CONVERSION_TYPE in HEAVY_OPERATIONS:
                    can_process, complexity_error = validate_file_for_operation(
                        input_path,
                        uploaded_file.size,
                        self.CONVERSION_TYPE,
                        user=request.user,
                    )
                    if not can_process:
                        cleanup_task_files(task_id)
                        return Response(
                            {"error": complexity_error},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                context["pdf_page_count"] = page_count

            # Get task kwargs from validated data (excluding file)
            task_kwargs = {
                k: v
                for k, v in serializer.validated_data.items()
                if k != self.FILE_FIELD_NAME and self._is_json_serializable(v)
            }

            # Log what we're filtering out
            for k, v in serializer.validated_data.items():
                if k != self.FILE_FIELD_NAME and not self._is_json_serializable(v):
                    logger.warning(
                        "Filtering non-serializable kwarg %s: %s", k, type(v)
                    )

            task_kwargs.update(self.get_task_kwargs(serializer.validated_data))

            # Log final kwargs for debugging
            logger.info("Final task kwargs: %s", task_kwargs)

            # Filter any remaining non-serializable objects from get_task_kwargs
            filtered_kwargs = {}
            for k, v in task_kwargs.items():
                if self._is_json_serializable(v):
                    filtered_kwargs[k] = v
                else:
                    logger.warning(
                        "Filtering non-serializable kwarg from get_task_kwargs %s: %s",
                        k,
                        type(v),
                    )

            # Start Celery task
            celery_task = self.get_celery_task()

            # Determine if user is premium for queue selection
            is_premium = self._is_premium_active(request)
            use_premium_queue = is_premium and getattr(
                settings, "PAYMENTS_ENABLED", True
            )

            # Add required parameters
            filtered_kwargs.update(
                {
                    "task_id": task_id,
                    "input_path": input_path,
                    "original_filename": uploaded_file.name,
                    "conversion_type": self.CONVERSION_TYPE,
                    "is_premium": is_premium,
                }
            )

            # Log filtered kwargs for debugging
            logger.info("Filtered kwargs before Celery: %s", filtered_kwargs)

            # Final serialization test
            try:
                import json

                json.dumps(filtered_kwargs)
                logger.info("JSON serialization test passed")
            except Exception as e:
                logger.error("JSON serialization failed: %s", e)
                for k, v in filtered_kwargs.items():
                    try:
                        json.dumps(v)
                    except Exception as ve:
                        logger.error(
                            "Non-serializable kwarg %s: %s - %s", k, type(v), ve
                        )

            result = celery_task.apply_async(
                kwargs=filtered_kwargs,
                task_id=task_id,
                queue=("premium" if use_premium_queue else "regular"),
            )

            logger.info(
                f"Started async {self.CONVERSION_TYPE} task",
                extra={
                    **context,
                    "task_id": task_id,
                    "celery_task_id": result.id,
                },
            )

            # Create signed task token for secure task control (cancel/background)
            task_token = create_task_token(
                task_id,
                request.user.id if request.user.is_authenticated else None,
            )

            # Return task ID immediately (fast response!)
            return Response(
                {
                    "task_id": task_id,
                    "task_token": task_token,
                    "status": "PENDING",
                    "message": "Conversion started. Poll /api/tasks/{task_id}/status/ for progress.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            cleanup_task_files(task_id)
            logger.exception(f"Failed to start async task: {e}")
            return Response(
                {"error": "Failed to start conversion. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskStatusAPIView(APIView):
    """Check status of an async conversion task."""

    def get(self, request: HttpRequest, task_id: str):
        """Get task status and progress."""
        try:
            task_token = _extract_task_token(request)
            if not _authorize_task_request(request, task_id, task_token):
                return Response({"error": "Unauthorized task access"}, status=403)

            result = AsyncResult(task_id)

            response_data = {
                "task_id": task_id,
                "status": result.status,
            }

            # Add progress info if available
            if result.status == "PROGRESS":
                # Task is reporting progress
                info = result.info or {}
                response_data["progress"] = info.get("progress", 0)
                response_data["current_step"] = info.get("current_step", "")
                response_data["total_steps"] = info.get("total_steps", 0)

            elif result.status == "SUCCESS":
                # Task completed successfully
                info = result.result or {}
                response_data["progress"] = 100
                response_data["output_filename"] = info.get("output_filename", "")
                response_data["message"] = "Conversion complete. Download your file."

            elif result.status == "FAILURE":
                # Task failed
                response_data["progress"] = 0
                response_data["error"] = (
                    str(result.result) if result.result else "Conversion failed"
                )

            elif result.status == "PENDING":
                # Task is waiting to be processed
                response_data["progress"] = 0
                response_data["message"] = "Waiting in queue..."

            elif result.status == "STARTED":
                # Task has started
                response_data["message"] = "Processing started..."

            elif result.status in ("REVOKED", "IGNORED"):
                # Task was cancelled by user
                response_data["progress"] = 0
                response_data["error"] = "Task was cancelled"
                response_data["cancelled"] = True
                # Normalize IGNORED to REVOKED so frontend handles it as cancelled
                if result.status == "IGNORED":
                    response_data["status"] = "REVOKED"

            return Response(response_data)

        except Exception as e:
            logger.exception(f"Error checking task status: {e}")
            return Response(
                {"error": "Failed to check task status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskResultAPIView(APIView):
    """Download result of a completed async conversion task."""

    def get(self, request: HttpRequest, task_id: str):
        """Download the conversion result."""
        try:
            task_token = _extract_task_token(request)
            if not _authorize_task_request(request, task_id, task_token):
                return Response({"error": "Unauthorized task access"}, status=403)

            result = AsyncResult(task_id)

            if result.status != "SUCCESS":
                return Response(
                    {
                        "error": f"Task is not complete. Status: {result.status}",
                        "task_id": task_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            info = result.result or {}
            output_path = info.get("output_path")
            output_filename = info.get("output_filename", "result")

            if not output_path or not os.path.exists(output_path):
                return Response(
                    {"error": "Result file not found. It may have expired."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Determine content type
            ext = os.path.splitext(output_path)[1].lower()
            content_types = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".doc": "application/msword",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".zip": "application/zip",
            }
            content_type = content_types.get(ext, "application/octet-stream")

            # Stream the file
            response = FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=output_filename,
            )
            response["Content-Type"] = content_type

            # Schedule cleanup after download (delayed)
            # Note: Actual cleanup happens via maintenance task
            logger.info(f"Serving result for task {task_id}: {output_filename}")

            return response

        except Exception as e:
            logger.exception(f"Error serving task result: {e}")
            return Response(
                {"error": "Failed to retrieve result"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request: HttpRequest, task_id: str):
        """Clean up task files (called by client after download)."""
        try:
            task_token = _extract_task_token(request)
            if not _authorize_task_request(request, task_id, task_token):
                return Response({"error": "Unauthorized task access"}, status=403)

            cleanup_task_files(task_id)

            # Forget the Celery result
            result = AsyncResult(task_id)
            result.forget()

            return Response(
                {"message": "Task cleaned up successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.warning(f"Error cleaning up task {task_id}: {e}")
            return Response(
                {"message": "Cleanup attempted"},
                status=status.HTTP_200_OK,
            )
