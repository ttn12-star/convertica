import os
import subprocess
import tempfile

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.exceptions import ConversionError, InvalidPDFError, StorageError

from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_word_file,
)
from ...logging_utils import get_logger

logger = get_logger(__name__)


def _check_libreoffice_available() -> bool:
    """Check if LibreOffice is installed and available."""
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def convert_word_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Convert DOC/DOCX → PDF using LibreOffice headless mode.

    Args:
        uploaded_file (UploadedFile): Word file (.doc/.docx)
        suffix (str): Suffix to append to output PDF filename.

    Returns:
        Tuple[str, str]: (path to original Word file, path to generated PDF)

    Raises:
        StorageError, ConversionError, InvalidPDFError
    """
    tmp_dir = tempfile.mkdtemp(prefix="doc2pdf_")

    # Get original filename for logging
    original_filename = uploaded_file.name if uploaded_file.name else "unknown"

    # Sanitize filename for filesystem safety
    safe_name = sanitize_filename(
        get_valid_filename(os.path.basename(original_filename))
    )

    # Ensure we have a valid extension
    if not safe_name.lower().endswith((".doc", ".docx")):
        # Try to preserve extension from original filename
        original_ext = os.path.splitext(original_filename)[1].lower()
        if original_ext in (".doc", ".docx"):
            safe_name = os.path.splitext(safe_name)[0] + original_ext

    context = {
        "function": "convert_word_to_pdf",
        "input_filename": safe_name,
        "original_filename": original_filename,
        "input_size": uploaded_file.size,
        "tmp_dir": tmp_dir,
    }

    try:
        # Check if LibreOffice is available
        if not _check_libreoffice_available():
            logger.error(
                "LibreOffice is not available",
                extra={**context, "event": "libreoffice_not_found"},
            )
            raise ConversionError(
                "LibreOffice is not installed or not available in PATH", context=context
            )

        # Check disk space
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        docx_path = os.path.join(tmp_dir, safe_name)
        base_name, _ = os.path.splitext(safe_name)
        pdf_name = f"{base_name}{suffix}.pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)

        context.update(
            {
                "docx_path": docx_path,
                "pdf_path": pdf_path,
            }
        )

        # Write uploaded file to temp
        try:
            logger.debug(
                "Writing Word file to temporary location",
                extra={**context, "event": "file_write_start"},
            )
            with open(docx_path, "wb") as f:
                bytes_written = 0
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
                    bytes_written += len(chunk)
            context["bytes_written"] = bytes_written
            logger.debug(
                "File written successfully",
                extra={**context, "event": "file_write_success"},
            )
        except OSError as err:
            logger.error(
                "Failed to write Word file to temp",
                extra={**context, "event": "file_write_error", "error": str(err)},
                exc_info=True,
            )
            raise StorageError(
                f"Failed to write Word file to temp: {err}",
                context={**context, "error_type": type(err).__name__},
            ) from err

        # Validate Word file before conversion
        is_valid, validation_error = validate_word_file(docx_path, context)
        if not is_valid:
            # Log file details for debugging
            try:
                file_size = os.path.getsize(docx_path)
                with open(docx_path, "rb") as f:
                    header_bytes = f.read(16)
                    header_hex = header_bytes.hex()

                logger.warning(
                    "Word file validation failed",
                    extra={
                        **context,
                        "validation_error": validation_error,
                        "file_size": file_size,
                        "header_hex": header_hex,
                        "event": "word_validation_failed",
                    },
                )
            except Exception as log_err:
                logger.warning(
                    "Could not log file details",
                    extra={**context, "log_error": str(log_err)},
                )

            raise InvalidPDFError(
                validation_error or "Invalid Word file structure", context=context
            )

        # Perform LibreOffice conversion with improved settings
        logger.info(
            "Starting LibreOffice conversion",
            extra={**context, "event": "conversion_start"},
        )
        try:
            # Use improved LibreOffice parameters
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--nodefault",
                    "--nolockcheck",
                    "--nologo",
                    "--norestore",
                    "--invisible",
                    "--convert-to",
                    "pdf:writer_pdf_Export",
                    "--outdir",
                    tmp_dir,
                    docx_path,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 10 minute timeout (increased for large files)
                cwd=tmp_dir,  # Set working directory
            )
            stdout = result.stdout.decode("utf-8", errors="ignore")
            stderr = result.stderr.decode("utf-8", errors="ignore")

            logger.debug(
                "LibreOffice conversion completed",
                extra={
                    **context,
                    "event": "libreoffice_complete",
                    "stdout": stdout[:500] if stdout else None,
                    "stderr": stderr[:500] if stderr else None,
                },
            )
        except subprocess.TimeoutExpired as e:
            logger.error(
                "LibreOffice conversion timeout",
                extra={**context, "event": "conversion_timeout", "timeout": 600},
                exc_info=True,
            )
            raise ConversionError(
                "LibreOffice conversion timed out after 10 minutes. File may be too large or complex.",
                context={**context, "error_type": "TimeoutExpired"},
            ) from e
        except subprocess.CalledProcessError as e:
            stderr = (
                e.stderr.decode("utf-8", errors="ignore")
                if e.stderr
                else "Unknown error"
            )
            stdout = e.stdout.decode("utf-8", errors="ignore") if e.stdout else ""

            # Enhanced error detection
            error_msg = stderr.lower()
            if "password" in error_msg or "protected" in error_msg:
                logger.warning(
                    "Word file appears to be password-protected",
                    extra={
                        **context,
                        "event": "protected_file_error",
                        "stderr": stderr[:500],
                    },
                )
                raise ConversionError(
                    "Word file is password-protected and cannot be converted",
                    context={**context, "error_type": "ProtectedFile"},
                ) from e

            logger.error(
                "LibreOffice conversion failed",
                extra={
                    **context,
                    "event": "conversion_error",
                    "return_code": e.returncode,
                    "stderr": stderr[:500],
                    "stdout": stdout[:500] if stdout else None,
                },
                exc_info=True,
            )
            raise ConversionError(
                f"LibreOffice conversion failed: {stderr[:200]}",
                context={
                    **context,
                    "error_type": "CalledProcessError",
                    "return_code": e.returncode,
                },
            ) from e

        # Verify output file exists with improved search
        if not os.path.exists(pdf_path):
            # LibreOffice might create PDF with different name (especially for .doc files)
            # Search for any PDF file in the directory
            pdf_files = [f for f in os.listdir(tmp_dir) if f.endswith(".pdf")]

            if pdf_files:
                # Prefer file that starts with base_name, otherwise take first PDF
                preferred = [f for f in pdf_files if f.startswith(base_name)]
                found_file = preferred[0] if preferred else pdf_files[0]
                pdf_path = os.path.join(tmp_dir, found_file)

                logger.info(
                    "PDF file found with alternative name",
                    extra={
                        **context,
                        "event": "pdf_found_alternative",
                        "found_filename": found_file,
                        "all_pdfs": pdf_files,
                    },
                )
            else:
                logger.error(
                    "PDF output file not created",
                    extra={
                        **context,
                        "event": "output_file_missing",
                        "tmp_dir_contents": os.listdir(tmp_dir),
                    },
                )
                raise ConversionError(
                    "PDF output file not created. LibreOffice conversion may have failed.",
                    context=context,
                )

        # Validate output PDF file
        is_valid, validation_error = validate_output_file(
            pdf_path, min_size=500, context=context
        )
        if not is_valid:
            logger.error(
                "Output PDF validation failed",
                extra={
                    **context,
                    "validation_error": validation_error,
                    "event": "output_validation_failed",
                },
            )
            raise ConversionError(
                validation_error or "Output PDF file is invalid", context=context
            )

        output_size = os.path.getsize(pdf_path)
        logger.info(
            "Word to PDF conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return docx_path, pdf_path

    except (StorageError, ConversionError, InvalidPDFError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during Word to PDF conversion",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
