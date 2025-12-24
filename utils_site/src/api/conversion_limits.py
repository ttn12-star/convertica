# Conversion limits and timeout utilities
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from functools import wraps
from typing import Any

# Use pypdf instead of PyMuPDF for better compatibility
try:
    from pypdf import PdfReader

    _pypdf_available = True
except ImportError:
    _pypdf_available = False

try:
    from django.utils.translation import gettext_lazy as _
except ImportError:
    # Fallback for non-Django context
    def _(text):
        return text


from .logging_utils import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONVERSION LIMITS - Adjust these values as needed
# ============================================================================

# Maximum number of pages allowed for PDF operations
MAX_PDF_PAGES = 30  # Keep 30 pages, monitor memory usage

# Stricter limits for heavy operations (memory-intensive)
MAX_PDF_PAGES_HEAVY = 30  # PDF to Word/Excel: fewer pages due to memory
MAX_FILE_SIZE_HEAVY = 15 * 1024 * 1024  # 15 MB for heavy operations

# Maximum file size in bytes (reduced for low-memory server)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB for free users
MAX_FILE_SIZE_PREMIUM = 200 * 1024 * 1024  # 200 MB for premium users

# Timeout for conversion operations in seconds
CONVERSION_TIMEOUT = 180  # 3 minutes max per conversion

# Timeout for simple operations (rotate, extract pages, etc.)
SIMPLE_OPERATION_TIMEOUT = 90  # 1.5 minutes

# Timeout for heavy operations (PDF to Word, PDF to Excel)
HEAVY_OPERATION_TIMEOUT = 300  # 5 minutes

# Heavy operations that need stricter limits
HEAVY_OPERATIONS = {
    "pdf_to_word",
    "pdf_to_excel",
    "word_to_pdf",
    "excel_to_pdf",
    "ppt_to_pdf",
    "html_to_pdf",
    "url_to_pdf",
}


# ============================================================================
# PDF VALIDATION
# ============================================================================


def get_max_file_size_for_user(user, operation: str = None) -> int:
    """Get maximum file size allowed for user based on subscription status.

    Args:
        user: Django user object
        operation: Type of operation (optional, for heavy operations)

    Returns:
        Maximum file size in bytes
    """
    operation_key = (operation or "").lower()

    if user.is_authenticated and hasattr(user, "is_premium") and user.is_premium:
        if hasattr(user, "is_subscription_active") and user.is_subscription_active():
            # Premium users get much higher limits
            return MAX_FILE_SIZE_PREMIUM  # 200 MB

    # Free users get standard limits
    if operation_key in HEAVY_OPERATIONS:
        return MAX_FILE_SIZE_HEAVY  # 15 MB for heavy operations
    return MAX_FILE_SIZE  # 25 MB for regular operations


def get_max_pages_for_user(user, operation: str = None) -> int:
    """Get maximum pages allowed for user based on subscription status.

    Args:
        user: Django user object
        operation: Type of operation (optional, for heavy operations)

    Returns:
        Maximum pages allowed
    """
    operation_key = (operation or "").lower()

    if user.is_authenticated and hasattr(user, "is_premium") and user.is_premium:
        if hasattr(user, "is_subscription_active") and user.is_subscription_active():
            premium_limits: dict[str, int] = {
                "pdf_to_word": 300,
                "pdf_to_excel": 300,
                "pdf_to_ppt": 300,
                "pdf_to_html": 300,
                "word_to_pdf": 300,
                "excel_to_pdf": 300,
                "ppt_to_pdf": 300,
                "html_to_pdf": 150,
                "url_to_pdf": 150,
                "pdf_to_jpg": 150,
                "compress_pdf": 400,
                "merge_pdf": 400,
                "split_pdf": 400,
                "rotate_pdf": 700,
                "crop_pdf": 700,
                "organize_pdf": 700,
                "extract_pages": 700,
                "remove_pages": 700,
                "unlock_pdf": 700,
                "protect_pdf": 700,
                "add_watermark": 700,
                "add_page_numbers": 700,
            }

            if operation_key in premium_limits:
                return premium_limits[operation_key]

            if operation_key in HEAVY_OPERATIONS:
                return 300
            return 400

    # Free users get standard limits
    if operation_key in HEAVY_OPERATIONS:
        return MAX_PDF_PAGES_HEAVY  # 50 for heavy operations
    return MAX_PDF_PAGES  # 50 for regular operations


def validate_pdf_pages(
    pdf_path: str, max_pages: int = MAX_PDF_PAGES, user=None, operation: str = None
) -> tuple[bool, str | None, int]:
    """Validate PDF doesn't exceed page limit.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum allowed pages (will be overridden by user limits)
        user: Django user object (optional)
        operation: Type of operation (optional)

    Returns:
        Tuple of (is_valid, error_message, page_count)
    """
    try:
        if not _pypdf_available:
            # Fallback if pypdf is not available - allow file but with warning
            logger.warning("pypdf not available, skipping page count validation")
            return True, None, 0  # Allow file but can't validate pages

        with open(pdf_path, "rb") as f:
            pdf_reader = PdfReader(f)
            page_count = len(pdf_reader.pages)

        # Get user-specific limit if user provided
        if user is not None:
            actual_max_pages = get_max_pages_for_user(user, operation)
        else:
            actual_max_pages = max_pages

        if page_count > actual_max_pages:
            # Check if user is premium for custom message
            is_premium = (
                user.is_authenticated
                and hasattr(user, "is_premium")
                and user.is_premium
                and hasattr(user, "is_subscription_active")
                and user.is_subscription_active()
            )

            if not is_premium and page_count > MAX_PDF_PAGES:
                # Free user exceeding limit - offer upgrade
                return (
                    False,
                    _(
                        "PDF has %(page_count)d pages (limit: %(max_pages)d). "
                        "You can split your file into smaller parts or get a 1-day Premium subscription for just $1 to process larger files with much higher limits!"
                    )
                    % {"page_count": page_count, "max_pages": MAX_PDF_PAGES},
                    page_count,
                )
            else:
                # Premium user exceeding their higher limit
                return (
                    False,
                    _(
                        "PDF has %(page_count)d pages, maximum allowed is %(max_pages)d. "
                        "Please split your PDF into smaller parts."
                    )
                    % {"page_count": page_count, "max_pages": actual_max_pages},
                    page_count,
                )

        return True, None, page_count

    except (ValueError, OSError) as e:
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
        if not _pypdf_available:
            # Fallback if pypdf is not available
            return 0

        with open(pdf_path, "rb") as f:
            pdf_reader = PdfReader(f)
            count = len(pdf_reader.pages)
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
            with ThreadPoolExecutor(
                max_workers=2
            ) as executor:  # Increased for low-memory server
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FuturesTimeoutError as exc:
                    logger.error(
                        "Operation timed out after %d seconds: %s",
                        timeout_seconds,
                        func.__name__,
                    )
                    raise ConversionTimeoutError(
                        f"Operation timed out after {timeout_seconds} seconds. "
                        f"The file may be too complex. Please try with a smaller file."
                    ) from exc

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

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:  # Increased for low-memory server
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            logger.error(
                "Operation timed out after %d seconds: %s",
                timeout,
                func.__name__,
            )
            raise ConversionTimeoutError(
                f"Operation timed out after {timeout} seconds. "
                f"The file may be too complex or corrupted. Please try with a smaller file."
            ) from exc


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


def validate_file_for_operation(
    pdf_path: str,
    file_size: int,
    operation: str,
    user=None,
) -> tuple[bool, str | None]:
    """Validate if file can be processed for given operation.

    Performs early validation to avoid starting operations that will likely fail.

    Args:
        pdf_path: Path to PDF file
        file_size: File size in bytes
        operation: Operation type (e.g., 'pdf_to_word')

    Returns:
        Tuple of (can_process, error_message)
    """
    is_heavy = operation in HEAVY_OPERATIONS

    # Check file size limits
    if user is not None:
        max_size = get_max_file_size_for_user(user, operation)
    else:
        max_size = MAX_FILE_SIZE_HEAVY if is_heavy else MAX_FILE_SIZE
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        return (
            False,
            _(
                "File is too large for this operation (%(file_mb).1f MB). "
                "Maximum size for %(operation)s is %(max_mb)d MB. "
                "Please use a smaller file or compress your PDF first."
            )
            % {
                "file_mb": file_mb,
                "operation": operation.replace("_", " "),
                "max_mb": max_mb,
            },
        )

    # Check page count
    if user is not None:
        max_pages = get_max_pages_for_user(user, operation)
    else:
        max_pages = MAX_PDF_PAGES_HEAVY if is_heavy else MAX_PDF_PAGES

    try:
        if not _pypdf_available:
            # Fallback if pypdf is not available - allow file but with warning
            logger.warning("pypdf not available, skipping page count validation")
            return True, None  # Allow file but can't validate pages

        with open(pdf_path, "rb") as f:
            pdf_reader = PdfReader(f)
            page_count = len(pdf_reader.pages)

        # Check page limit
        if page_count > max_pages:
            return (
                False,
                _(
                    "PDF has %(page_count)d pages. Maximum for %(operation)s is %(max_pages)d pages. "
                    "Please split your PDF into smaller parts."
                )
                % {
                    "page_count": page_count,
                    "operation": operation.replace("_", " "),
                    "max_pages": max_pages,
                },
            )

        # For heavy operations, check PDF complexity (images, scans)
        if is_heavy and page_count > 10:
            total_images = 0
            for _page_index in range(min(page_count, 5)):  # Check first 5 pages
                # Note: pypdf doesn't have get_images() method like PyMuPDF
                # This is a simplified check - image detection would need different approach
                total_images += 0  # Placeholder

            # If PDF has many images, it's likely a scan - warn user
            avg_images_per_page = total_images / min(page_count, 5)
            if avg_images_per_page > 2:
                # Estimate: scanned PDFs take much longer
                estimated_time = page_count * 10  # ~10 sec per page for scanned
                if estimated_time > HEAVY_OPERATION_TIMEOUT:
                    return (
                        False,
                        _(
                            "This PDF appears to be scanned (contains many images). "
                            "Scanned PDFs with %(page_count)d pages may take too long to process. "
                            "Please try with fewer pages (max ~%(max_pages)d for scanned PDFs)."
                        )
                        % {
                            "page_count": page_count,
                            "max_pages": HEAVY_OPERATION_TIMEOUT // 10,
                        },
                    )

        return True, None

    except (ValueError, OSError) as e:
        logger.warning("Failed to validate PDF for operation: %s", e)
        # If we can't validate, let conversion handle it
        return True, None


def can_process_file(
    file_size: int,
    page_count: int,
    operation: str,
) -> tuple[bool, str | None, int]:
    """Quick check if we can process file without reading it.

    Args:
        file_size: File size in bytes
        page_count: Number of pages (if known)
        operation: Operation type

    Returns:
        Tuple of (can_process, error_message, estimated_time_seconds)
    """
    is_heavy = operation in HEAVY_OPERATIONS

    # Check file size
    max_size = MAX_FILE_SIZE_HEAVY if is_heavy else MAX_FILE_SIZE
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return (
            False,
            _("File is too large (max %(max_mb)d MB for this operation).")
            % {"max_mb": max_mb},
            0,
        )

    # Check page count
    max_pages = MAX_PDF_PAGES_HEAVY if is_heavy else MAX_PDF_PAGES
    if page_count > max_pages:
        return (
            False,
            _("Too many pages (max %(max_pages)d for this operation).")
            % {"max_pages": max_pages},
            0,
        )

    # Estimate processing time
    estimated_time = estimate_processing_time(file_size, page_count, operation)

    # Check if it will likely timeout
    timeout = get_timeout_for_operation(operation, page_count, file_size)
    if estimated_time > timeout * 0.9:  # 90% of timeout
        return (
            False,
            _(
                "File is too complex for our server. "
                "Estimated processing time exceeds limits. "
                "Please try with a smaller file."
            ),
            estimated_time,
        )

    return True, None, estimated_time


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
        "excel_to_pdf": 4,
        "ppt_to_pdf": 5,
        "html_to_pdf": 2,
        "url_to_pdf": 3,
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
    op = (operation or "").lower()
    op_map = {
        "rotate_pdf": "rotate",
        "crop_pdf": "crop",
        "merge_pdf": "merge",
        "split_pdf": "split",
        "organize_pdf": "organize",
        "compress_pdf": "compress",
        "pdf_to_jpg": "pdf_to_jpg",
        "pdf_to_word": "pdf_to_word",
        "pdf_to_excel": "pdf_to_excel",
        "word_to_pdf": "word_to_pdf",
        "excel_to_pdf": "excel_to_pdf",
        "ppt_to_pdf": "ppt_to_pdf",
        "html_to_pdf": "html_to_pdf",
        "url_to_pdf": "url_to_pdf",
        "jpg_to_pdf": "jpg_to_pdf",
        "unlock_pdf": "unlock_pdf",
        "protect_pdf": "protect_pdf",
    }
    op = op_map.get(op, op)

    # Heavy operations that need more time
    heavy_operations = {
        "pdf_to_word",
        "pdf_to_excel",
        "word_to_pdf",
        "excel_to_pdf",
        "ppt_to_pdf",
        "html_to_pdf",
        "url_to_pdf",
    }

    # Simple operations that should be quick
    simple_operations = {
        "rotate",
        "rotate_pdf",
        "extract_pages",
        "remove_pages",
        "split",
        "split_pdf",
        "organize",
        "organize_pdf",
        "crop",
        "crop_pdf",
        "merge",
        "merge_pdf",
        "compress",
        "compress_pdf",
        "add_watermark",
        "add_page_numbers",
        "unlock_pdf",
        "protect_pdf",
    }

    if op in heavy_operations:
        base_timeout = HEAVY_OPERATION_TIMEOUT
    elif op in simple_operations:
        base_timeout = SIMPLE_OPERATION_TIMEOUT
    else:
        base_timeout = CONVERSION_TIMEOUT

    # Add extra time for large files
    if page_count > 20:
        base_timeout += (page_count - 20) * 2  # +2 sec per page over 20

    # Cap at 10 minutes for heavy files
    return min(base_timeout, 600)
