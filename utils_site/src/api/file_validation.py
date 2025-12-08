"""
File validation utilities for conversion APIs.
"""

import os
import shutil

from .logging_utils import get_logger

logger = get_logger(__name__)


# Magic numbers for file type detection
PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"  # DOCX is a ZIP file
DOC_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # OLE2 format (old .doc)


def validate_pdf_file(file_path: str, context: dict) -> tuple[bool, str | None]:
    """
    Validate PDF file structure.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
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
            if len(reader.pages) == 0:
                return False, "PDF has no pages"

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

        return True, None

    except Exception as e:
        logger.error(
            "Error during PDF validation",
            extra={**context, "error": str(e), "event": "pdf_validation_error"},
            exc_info=True,
        )
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
                # Magic number not found - try extension-based validation
                if is_docx:
                    # Try to validate as DOCX even without magic number
                    # (some files might have BOM or other prefixes)
                    try:
                        import zipfile

                        with zipfile.ZipFile(file_path, "r") as zip_file:
                            file_list = zip_file.namelist()
                            if any(
                                "word/document.xml" in f or "[Content_Types]" in f
                                for f in file_list
                            ):
                                logger.info(
                                    "DOCX validated by structure despite missing magic number",
                                    extra={
                                        **context,
                                        "event": "docx_structure_validation",
                                    },
                                )
                                return True, None
                    except Exception as zip_err:
                        logger.debug(
                            "Extension-based DOCX validation failed",
                            extra={
                                **context,
                                "error": str(zip_err),
                                "event": "docx_extension_validation_failed",
                            },
                        )

                # Log header for debugging
                header_hex = header[:8].hex() if len(header) >= 8 else header.hex()
                logger.warning(
                    "Word file magic number not recognized",
                    extra={
                        **context,
                        "header_hex": header_hex,
                        "file_ext": file_ext,
                        "file_size": file_size,
                        "event": "word_magic_number_unknown",
                    },
                )

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
