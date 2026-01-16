"""
File validation utilities for conversion APIs.
"""

import os
import shutil

from .cache_utils import (
    cache_pdf_page_count,
    cache_pdf_validation,
    get_cached_pdf_validation,
)
from .logging_utils import get_logger

logger = get_logger(__name__)


# Magic numbers for file type detection
PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"  # DOCX is a ZIP file
DOC_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # OLE2 format (old .doc)


def validate_pdf_file(file_path: str, context: dict) -> tuple[bool, str | None]:
    """
    Validate PDF file structure with caching.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check cache first
    cached_result = get_cached_pdf_validation(file_path)
    if cached_result is not None:
        logger.debug("Using cached PDF validation result", extra=context)
        return (
            (cached_result, None)
            if cached_result
            else (False, "Cached validation failed")
        )

    try:
        # Check file exists and is not empty
        if not os.path.exists(file_path):
            return False, "PDF file does not exist"

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "PDF file is empty"

        if file_size < 100:  # Minimum PDF size
            return False, "PDF file is too small to be valid"

        # Check magic number
        with open(file_path, "rb") as f:
            header = f.read(4)
            if not header.startswith(PDF_MAGIC):
                return (
                    False,
                    "File does not appear to be a valid PDF (missing PDF header)",
                )

        # Try to read PDF structure with PyPDF2
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)

            # Check if PDF is encrypted
            if reader.is_encrypted:
                return False, "PDF is password-protected"

            # Check if PDF has pages
            page_count = len(reader.pages)
            if page_count == 0:
                return False, "PDF has no pages"

            # Cache page count for future use
            cache_pdf_page_count(file_path, page_count)

            # Try to access first page to verify it's readable
            try:
                first_page = reader.pages[0]
                _ = first_page.extract_text()  # Try to extract text
            except Exception as e:
                logger.warning(
                    "PDF page extraction test failed",
                    extra={
                        **context,
                        "error": str(e),
                        "event": "pdf_validation_warning",
                    },
                )
                # Don't fail validation, just log warning

        except ImportError:
            # PyPDF2 not available, skip deep validation
            logger.debug(
                "PyPDF2 not available, skipping deep PDF validation", extra=context
            )
        except Exception as e:
            logger.warning(
                "PDF validation with PyPDF2 failed",
                extra={**context, "error": str(e), "event": "pdf_validation_warning"},
            )
            # Don't fail validation if PyPDF2 has issues

        # Cache successful validation
        cache_pdf_validation(file_path, True)
        return True, None

    except Exception as e:
        logger.error(
            "Error during PDF validation",
            extra={**context, "error": str(e), "event": "pdf_validation_error"},
            exc_info=True,
        )
        # Cache failed validation (shorter timeout)
        cache_pdf_validation(file_path, False, timeout=300)  # 5 minutes
        return False, f"Error validating PDF: {str(e)}"


def validate_word_file(file_path: str, context: dict) -> tuple[bool, str | None]:
    """
    Validate Word file structure (.doc or .docx).

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        # Check file exists and is not empty
        if not os.path.exists(file_path):
            return False, "Word file does not exist"

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Word file is empty"

        # Get file extension for additional validation
        file_ext = os.path.splitext(file_path)[1].lower()
        is_docx = file_ext == ".docx"
        is_doc = file_ext == ".doc"

        # Check magic number
        with open(file_path, "rb") as f:
            header = f.read(16)  # Read more bytes for better detection

            # Check for DOCX (ZIP format) - PK\x03\x04
            if header.startswith(DOCX_MAGIC):
                # DOCX is a ZIP file, try to validate it
                try:
                    import zipfile

                    with zipfile.ZipFile(file_path, "r") as zip_file:
                        # Check for required DOCX structure
                        required_files = ["[Content_Types].xml", "word/document.xml"]
                        file_list = zip_file.namelist()
                        if not any(req in file_list for req in required_files):
                            logger.warning(
                                "DOCX missing required files",
                                extra={
                                    **context,
                                    "file_list": file_list[:10],
                                    "event": "docx_structure_warning",
                                },
                            )
                            # If extension is .docx, still consider it valid if it's a valid ZIP
                            if is_docx:
                                return True, None
                            return False, "DOCX file structure is invalid"
                except zipfile.BadZipFile as zip_err:
                    logger.warning(
                        "DOCX ZIP validation failed",
                        extra={
                            **context,
                            "error": str(zip_err),
                            "event": "docx_zip_error",
                        },
                    )
                    # If extension is .docx, be more lenient
                    if is_docx and file_size > 100:
                        logger.info(
                            "Allowing DOCX file despite ZIP validation error (extension-based)",
                            extra={**context, "event": "docx_lenient_validation"},
                        )
                        return True, None
                    return False, "DOCX file is not a valid ZIP archive"
                except Exception as e:
                    logger.warning(
                        "DOCX validation warning",
                        extra={
                            **context,
                            "error": str(e),
                            "event": "docx_validation_warning",
                        },
                    )
                    # If extension is .docx and file size is reasonable, allow it
                    if is_docx and file_size > 100:
                        logger.info(
                            "Allowing DOCX file despite validation warning (extension-based)",
                            extra={**context, "event": "docx_lenient_validation"},
                        )
                        return True, None
                return True, None

            # Check for old DOC format (OLE2) - \xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1
            elif header.startswith(DOC_MAGIC):
                # Old .doc format - basic validation only
                if file_size < 1000:  # Minimum reasonable size
                    return False, "DOC file is too small to be valid"
                return True, None

            else:
                # Magic number not found - try extension-based lenient validation
                if is_docx:
                    # Try to validate as DOCX even without magic number
                    # (some files might have BOM or other prefixes)
                    try:
                        import zipfile

                        with zipfile.ZipFile(file_path, "r") as zip_file:
                            # Basic check: can list files and verify structure
                            namelist = zip_file.namelist()
                            # More robust check for DOCX structure
                            has_content_types = "[Content_Types].xml" in namelist
                            has_word_dir = any("word/" in name for name in namelist)

                            if not (has_content_types or has_word_dir):
                                raise ValueError("Missing DOCX structure")

                        logger.info(
                            "DOCX validated by zip structure despite missing magic number",
                            extra={**context, "event": "docx_structure_validated"},
                        )
                        return True, None
                    except Exception as e:
                        logger.warning(
                            "DOCX extension-based validation warning",
                            extra={
                                **context,
                                "error": str(e),
                                "event": "docx_extension_validation_warning",
                            },
                        )
                        if file_size > 1000:
                            logger.info(
                                "Allowing DOCX file despite header/zip warning (lenient)",
                                extra={**context, "event": "docx_lenient_extension"},
                            )
                            return True, None
                        return False, "File does not appear to be a valid Word document"

                elif is_doc:
                    if file_size < 1000:  # Minimum reasonable size
                        return False, "DOC file is too small to be valid"

                # If extension is .docx or .doc and file size is reasonable, be lenient
                if (is_docx or is_doc) and file_size > 100:
                    logger.info(
                        "Allowing Word file based on extension and size (lenient validation)",
                        extra={
                            **context,
                            "file_ext": file_ext,
                            "file_size": file_size,
                            "event": "word_lenient_validation",
                        },
                    )
                    return True, None

                # Generate header hex for error message
                header_hex = header[:8].hex() if len(header) >= 8 else header.hex()
                return (
                    False,
                    f"File does not appear to be a valid Word document (header: {header_hex[:16]})",
                )

    except Exception as e:
        logger.error(
            "Error during Word file validation",
            extra={**context, "error": str(e), "event": "word_validation_error"},
            exc_info=True,
        )
        return False, f"Error validating Word file: {str(e)}"


def check_disk_space(path: str, required_mb: int = 100) -> tuple[bool, str | None]:
    """
    Check if there's enough disk space available.

    Args:
        path: Path to check disk space for
        required_mb: Required space in MB

    Returns:
        Tuple[bool, Optional[str]]: (has_space, error_message)
    """
    try:
        stat = shutil.disk_usage(path)
        free_mb = stat.free / (1024 * 1024)

        if free_mb < required_mb:
            return (
                False,
                f"Insufficient disk space. Required: {required_mb} MB, Available: {free_mb:.1f} MB",
            )

        return True, None
    except Exception as e:
        logger.warning(
            "Could not check disk space",
            extra={"path": path, "error": str(e), "event": "disk_space_check_warning"},
        )
        # Don't fail if we can't check disk space
        return True, None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename to remove problematic characters.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Remove or replace problematic characters
    # Keep alphanumeric, spaces, dots, hyphens, underscores
    import re

    filename = re.sub(r"[^\w\s\.\-]", "_", filename)

    # Remove multiple consecutive spaces/underscores
    filename = re.sub(r"[\s_]+", "_", filename)

    # Trim
    filename = filename.strip("._-")

    # Ensure it's not empty
    if not filename:
        filename = "file"

    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext

    return filename


def encode_filename_for_header(filename: str) -> str:
    """
    Encode filename for Content-Disposition header according to RFC 5987.
    Supports non-ASCII characters (Cyrillic, CJK, Arabic, etc.)

    Args:
        filename: Filename (may contain Unicode characters)

    Returns:
        Properly encoded Content-Disposition value

    Examples:
        >>> encode_filename_for_header("document.pdf")
        'attachment; filename="document.pdf"'
        >>> encode_filename_for_header("документ.pdf")
        'attachment; filename="file.pdf"; filename*=UTF-8\'\'%D0%B4%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.pdf'
    """
    from urllib.parse import quote

    try:
        # Try to encode as ASCII (for backward compatibility)
        filename.encode("ascii")
        # ASCII filenames can be used directly
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        # Non-ASCII filenames - encode per RFC 5987
        encoded = quote(filename.encode("utf-8"))
        # Use dual header for maximum compatibility

        # Extract extension first
        name_part = "file"
        ext_part = ""
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            # Try to keep extension if it's ASCII
            try:
                ext.encode("ascii")
                ext_part = f".{ext}"
            except UnicodeEncodeError:
                ext_part = ""
            # Try to extract ASCII chars from name
            ascii_name = name.encode("ascii", errors="ignore").decode("ascii")
            if ascii_name and ascii_name != ".":
                name_part = ascii_name.strip("._-") or "file"
        else:
            # No extension - try to get ASCII chars from whole filename
            ascii_name = filename.encode("ascii", errors="ignore").decode("ascii")
            if ascii_name and ascii_name != ".":
                name_part = ascii_name.strip("._-") or "file"

        ascii_fallback = f"{name_part}{ext_part}"
        return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def validate_output_file(
    file_path: str, min_size: int = 100, context: dict = None
) -> tuple[bool, str | None]:
    """
    Validate that output file was created successfully.

    Args:
        file_path: Path to output file
        min_size: Minimum expected file size in bytes
        context: Logging context

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if context is None:
        context = {}

    try:
        if not os.path.exists(file_path):
            return False, "Output file was not created"

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Output file is empty"

        if file_size < min_size:
            logger.warning(
                "Output file is suspiciously small",
                extra={
                    **context,
                    "file_path": file_path,
                    "file_size": file_size,
                    "event": "small_output_file",
                },
            )
            # Don't fail, just warn

        return True, None

    except Exception as e:
        logger.error(
            "Error validating output file",
            extra={
                **context,
                "file_path": file_path,
                "error": str(e),
                "event": "output_validation_error",
            },
            exc_info=True,
        )
        return False, f"Error validating output file: {str(e)}"
