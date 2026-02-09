"""
Structured logging utilities for API views.
"""

import logging
import os
import time
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)


def build_request_context(
    request, uploaded_file: UploadedFile | None = None, **additional_context: Any
) -> dict[str, Any]:
    """
    Build structured context dictionary for logging.

    Args:
        request: Django request object
        uploaded_file: Optional uploaded file
        **additional_context: Additional context to include

    Returns:
        Dictionary with structured context
    """
    context = {
        "request_id": getattr(request, "id", None),
        "user_agent": request.META.get("HTTP_USER_AGENT", "Unknown"),
        "remote_addr": request.META.get("REMOTE_ADDR", "Unknown"),
        "method": request.method,
        "path": request.path,
    }

    if uploaded_file:
        context.update(
            {
                "uploaded_filename": get_valid_filename(
                    os.path.basename(uploaded_file.name)
                ),
                "file_size": uploaded_file.size,
                "file_size_mb": round(uploaded_file.size / (1024 * 1024), 2),
                "content_type": getattr(uploaded_file, "content_type", "Unknown"),
            }
        )

    context.update(additional_context)
    return context


def log_conversion_start(
    logger: logging.Logger, conversion_type: str, context: dict[str, Any]
) -> float:
    """
    Log the start of a conversion operation.

    Args:
        logger: Logger instance
        conversion_type: Type of conversion (e.g., "PDF_TO_WORD")
        context: Request context

    Returns:
        Start time for performance measurement
    """
    start_time = time.time()
    logger.info(
        f"Starting {conversion_type} conversion",
        extra={
            **context,
            "event": "conversion_start",
            "conversion_type": conversion_type,
        },
    )
    return start_time


def log_conversion_success(
    logger: logging.Logger,
    conversion_type: str,
    context: dict[str, Any],
    start_time: float,
    output_filename: str | None = None,
    **additional_info: Any,
):
    """
    Log successful conversion.

    Args:
        logger: Logger instance
        conversion_type: Type of conversion
        context: Request context
        start_time: Start time from log_conversion_start
        output_filename: Name of output file
        **additional_info: Additional information to log
    """
    processing_time = time.time() - start_time
    log_data = {
        **context,
        "event": "conversion_success",
        "conversion_type": conversion_type,
        "processing_time_seconds": round(processing_time, 3),
        "processing_time_ms": round(processing_time * 1000, 2),
        "output_filename": output_filename,
        **additional_info,
    }
    logger.info(f"{conversion_type} conversion completed successfully", extra=log_data)

    # Send metrics to Sentry using Metrics API (non-blocking, async)
    try:
        from sentry_sdk import metrics

        # Count successful conversions
        metrics.count(
            "conversion.success", 1, tags={"conversion_type": conversion_type}
        )
        # Track processing time distribution
        metrics.distribution(
            "conversion.processing_time",
            processing_time,
            unit="second",
            tags={"conversion_type": conversion_type},
        )
        # Track file size if available
        if "file_size_mb" in log_data:
            metrics.distribution(
                "conversion.file_size",
                log_data["file_size_mb"],
                unit="megabyte",
                tags={"conversion_type": conversion_type},
            )
    except ImportError:
        # Sentry not installed, skip
        pass
    except Exception:
        # Don't fail if Sentry is down
        pass


def log_conversion_error(
    logger: logging.Logger,
    conversion_type: str,
    context: dict[str, Any],
    error: Exception,
    start_time: float | None = None,
    level: str = "error",
    **additional_info: Any,
):
    """
    Log conversion error with full context.

    Args:
        logger: Logger instance
        conversion_type: Type of conversion
        context: Request context
        error: Exception that occurred
        start_time: Optional start time for performance measurement
        level: Log level ("error", "warning", "info")
        **additional_info: Additional information to log
    """
    log_data = {
        **context,
        "event": "conversion_error",
        "conversion_type": conversion_type,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
    }

    if start_time:
        processing_time = time.time() - start_time
        log_data.update(
            {
                "processing_time_seconds": round(processing_time, 3),
                "processing_time_ms": round(processing_time * 1000, 2),
            }
        )

    # Add exception context if available
    if hasattr(error, "context"):
        log_data["error_context"] = error.context

    log_data.update(additional_info)

    log_method = getattr(logger, level, logger.error)
    if level == "exception":
        log_method(
            f"{conversion_type} conversion failed: {error}",
            exc_info=True,
            extra=log_data,
        )
    else:
        log_method(f"{conversion_type} conversion failed: {error}", extra=log_data)

    # Explicitly send ERROR logs to Sentry
    if level in ("error", "exception"):
        try:
            import sentry_sdk

            sentry_sdk.logger.error(
                f"{conversion_type} conversion failed: {error}",
                exc_info=(level == "exception"),
                extra=log_data,
            )
        except (ImportError, Exception):
            pass  # Sentry not available

    # Send error metrics to Sentry
    try:
        from sentry_sdk import metrics

        metrics.count(
            "conversion.error",
            1,
            tags={
                "conversion_type": conversion_type,
                "error_type": error.__class__.__name__,
            },
        )
    except (ImportError, Exception):
        # Don't fail if Sentry is unavailable
        pass


def log_validation_error(
    logger: logging.Logger, serializer_errors: dict[str, Any], context: dict[str, Any]
):
    """Log serializer validation errors."""
    logger.warning(
        "Request validation failed",
        extra={
            **context,
            "event": "validation_error",
            "validation_errors": serializer_errors,
        },
    )


def log_file_validation_error(
    logger: logging.Logger, reason: str, context: dict[str, Any], **additional_info: Any
):
    """Log file validation errors (size, type, etc.).

    Uses INFO level because these are expected user errors (wrong file size/type),
    not application bugs. This prevents them from cluttering Sentry.
    """
    logger.info(
        f"File validation failed: {reason}",
        extra={
            **context,
            "event": "file_validation_error",
            "validation_reason": reason,
            **additional_info,
        },
    )
