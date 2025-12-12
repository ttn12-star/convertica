# Conversion limits and timeout utilities
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from functools import wraps
from typing import Any

import fitz  # PyMuPDF
from django.utils.translation import gettext_lazy as _

from .logging_utils import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONVERSION LIMITS - Adjust these values as needed
# ============================================================================

# Maximum number of pages allowed for PDF operations
MAX_PDF_PAGES = 50  # Increase to 50 if needed, 20 is safe for low-memory servers

# Maximum file size in bytes (50 MB default)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Timeout for conversion operations in seconds
CONVERSION_TIMEOUT = 120  # 2 minutes max per conversion

# Timeout for simple operations (rotate, extract pages, etc.)
SIMPLE_OPERATION_TIMEOUT = 60  # 1 minute

# Timeout for heavy operations (PDF to Word, PDF to Excel)
HEAVY_OPERATION_TIMEOUT = 180  # 3 minutes


# ============================================================================
# PDF VALIDATION
# ============================================================================


def validate_pdf_pages(
    pdf_path: str, max_pages: int = MAX_PDF_PAGES
) -> tuple[bool, str | None, int]:
    """Validate PDF doesn't exceed page limit.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum allowed pages

    Returns:
        Tuple of (is_valid, error_message, page_count)
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        if page_count > max_pages:
            return (
                False,
                _(
                    "PDF has %(page_count)d pages, maximum allowed is %(max_pages)d. Please split your PDF into smaller parts."
                )
                % {"page_count": page_count, "max_pages": max_pages},
                page_count,
            )

        return True, None, page_count

    except Exception as e:
        logger.warning("Failed to validate PDF pages: %s", e)
        # If we can't read the PDF, let the conversion handle the error
        return True, None, 0


def get_pdf_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Number of pages, or 0 if unable to read
    """
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


# ============================================================================
# TIMEOUT WRAPPER
# ============================================================================


class ConversionTimeoutError(Exception):
    """Raised when a conversion operation times out."""

    pass


def with_timeout(timeout_seconds: int = CONVERSION_TIMEOUT):
    """Decorator to add timeout to a function.

    Uses ThreadPoolExecutor for cross-platform compatibility.

    Args:
        timeout_seconds: Maximum time allowed for the function to execute

    Example:
        @with_timeout(60)
        def slow_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    logger.error(
                        "Operation timed out after %d seconds: %s",
                        timeout_seconds,
                        func.__name__,
                    )
                    raise ConversionTimeoutError(
                        f"Operation timed out after {timeout_seconds} seconds. "
                        f"The file may be too complex. Please try with a smaller file."
                    )

        return wrapper

    return decorator


def run_with_timeout(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    timeout: int = CONVERSION_TIMEOUT,
) -> Any:
    """Run a function with a timeout.

    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        timeout: Maximum time allowed in seconds

    Returns:
        Function result

    Raises:
        ConversionTimeoutError: If the function times out
    """
    if kwargs is None:
        kwargs = {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.error(
                "Operation timed out after %d seconds: %s",
                timeout,
                func.__name__,
            )
            raise ConversionTimeoutError(
                f"Operation timed out after {timeout} seconds. "
                f"The file may be too complex or corrupted. Please try with a smaller file."
            )


# ============================================================================
# MEMORY PROTECTION
# ============================================================================


def check_available_memory(required_mb: int = 100) -> tuple[bool, str | None]:
    """Check if enough memory is available for the operation.

    Args:
        required_mb: Required memory in megabytes

    Returns:
        Tuple of (is_ok, error_message)
    """
    try:
        import psutil

        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)

        if available_mb < required_mb:
            return (
                False,
                "Server is currently under heavy load. "
                "Please try again in a few minutes.",
            )

        return True, None
    except ImportError:
        # psutil not installed, skip check
        return True, None
    except Exception as e:
        logger.warning("Failed to check memory: %s", e)
        return True, None


# ============================================================================
# FILE SIZE ESTIMATION
# ============================================================================


def estimate_processing_time(file_size: int, page_count: int, operation: str) -> int:
    """Estimate processing time based on file size and page count.

    Args:
        file_size: File size in bytes
        page_count: Number of pages
        operation: Type of operation (e.g., 'pdf_to_word', 'compress')

    Returns:
        Estimated time in seconds
    """
    # Base estimates per page (in seconds)
    time_per_page = {
        "pdf_to_word": 3,
        "pdf_to_excel": 5,
        "pdf_to_jpg": 1,
        "compress": 0.5,
        "merge": 0.2,
        "split": 0.2,
        "rotate": 0.1,
        "watermark": 0.5,
        "default": 1,
    }

    base_time = time_per_page.get(operation, time_per_page["default"])

    # Factor in file size (larger files take longer)
    size_factor = 1 + (file_size / (10 * 1024 * 1024))  # +1 for every 10MB

    estimated_time = int(base_time * page_count * size_factor)

    # Add minimum buffer
    return max(estimated_time, 10)


def get_timeout_for_operation(
    operation: str, page_count: int = 1, file_size: int = 0
) -> int:
    """Get appropriate timeout for an operation.

    Args:
        operation: Type of operation
        page_count: Number of pages
        file_size: File size in bytes

    Returns:
        Timeout in seconds
    """
    # Heavy operations that need more time
    heavy_operations = {"pdf_to_word", "pdf_to_excel"}

    # Simple operations that should be quick
    simple_operations = {"rotate", "extract_pages", "remove_pages", "split", "organize"}

    if operation in heavy_operations:
        base_timeout = HEAVY_OPERATION_TIMEOUT
    elif operation in simple_operations:
        base_timeout = SIMPLE_OPERATION_TIMEOUT
    else:
        base_timeout = CONVERSION_TIMEOUT

    # Add extra time for large files
    if page_count > 20:
        base_timeout += (page_count - 20) * 2  # +2 sec per page over 20

    # Cap at 5 minutes
    return min(base_timeout, 300)
