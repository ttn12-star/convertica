# services/convert.py
import os
import tempfile
from typing import Tuple

from pdf2docx import Converter
from django.core.files.uploadedfile import UploadedFile

from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)
from ...logging_utils import get_logger
from ...file_validation import (
    validate_pdf_file,
    check_disk_space,
    sanitize_filename,
    validate_output_file,
)

logger = get_logger(__name__)


def convert_pdf_to_docx(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Save uploaded PDF to temp, convert it to DOCX and return (pdf_path, docx_path).

    Args:
        uploaded_file (UploadedFile): Uploaded PDF file.
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_pdf, path_to_docx) where docx exists.

    Raises:
        EncryptedPDFError: when the PDF appears to be password-protected.
        InvalidPDFError: when pdf is malformed and conversion fails.
        StorageError: for filesystem I/O errors.
        ConversionError: for other conversion-related failures.
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "convert_pdf_to_docx",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
    }

    try:
        # Check disk space before starting
        tmp_dir = tempfile.mkdtemp(prefix="pdf2docx_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)  # 200 MB for safety
        if not disk_check:
            raise StorageError(
                disk_error or "Insufficient disk space",
                context=context
            )
        
        logger.debug("Created temporary directory", extra={**context, "event": "temp_dir_created"})

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        docx_name = f"{base}{suffix}.docx"
        docx_path = os.path.join(tmp_dir, docx_name)

        context.update({
            "pdf_path": pdf_path,
            "docx_path": docx_path,
        })

        # Write uploaded file to temp
        try:
            logger.debug("Writing uploaded file to temporary location", extra={**context, "event": "file_write_start"})
            with open(pdf_path, "wb") as f:
                bytes_written = 0
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
                    bytes_written += len(chunk)
            context["bytes_written"] = bytes_written
            logger.debug("File written successfully", extra={**context, "event": "file_write_success"})
        except (OSError, IOError) as io_err:
            logger.error(
                "Failed to write uploaded file",
                extra={**context, "event": "file_write_error", "error": str(io_err)},
                exc_info=True
            )
            raise StorageError(
                f"Failed to write uploaded file: {io_err}",
                context={**context, "error_type": type(io_err).__name__}
            ) from io_err

        # Validate PDF file before conversion
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in validation_error.lower() or "encrypted" in validation_error.lower():
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected",
                    context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file",
                context=context
            )

        # Perform conversion with optimized parameters
        try:
            logger.info("Starting PDF to DOCX conversion", extra={**context, "event": "conversion_start"})
            
            # Create converter with optimized settings
            cv = Converter(pdf_path)
            try:
                # Convert with better quality settings
                # pdf2docx supports pages parameter for selective conversion
                cv.convert(
                    docx_path,
                    start=0,  # Start from first page
                    end=None,  # Convert all pages
                    pages=None,  # Convert all pages
                )
                logger.debug("Conversion completed", extra={**context, "event": "conversion_complete"})
            finally:
                cv.close()
        except Exception as conv_exc:
            msg = str(conv_exc).lower()
            error_context = {**context, "error_type": type(conv_exc).__name__, "error_message": str(conv_exc)}
            
            # Enhanced error detection
            if any(keyword in msg for keyword in ["encrypted", "password", "security", "permission"]):
                logger.warning(
                    "PDF is encrypted/password protected",
                    extra={**error_context, "event": "encrypted_pdf_error"}
                )
                raise EncryptedPDFError(
                    "PDF is encrypted/password protected",
                    context=error_context
                ) from conv_exc
            
            if any(keyword in msg for keyword in ["error", "parse", "format", "corrupt", "invalid", "malformed"]):
                logger.warning(
                    "Invalid PDF structure detected",
                    extra={**error_context, "event": "invalid_pdf_error"}
                )
                raise InvalidPDFError(
                    f"Invalid PDF structure: {conv_exc}",
                    context=error_context
                ) from conv_exc
            
            logger.error(
                "PDF conversion failed",
                extra={**error_context, "event": "conversion_error"},
                exc_info=True
            )
            raise ConversionError(
                f"Conversion failed: {conv_exc}",
                context=error_context
            ) from conv_exc

        # Validate output file
        is_valid, validation_error = validate_output_file(docx_path, min_size=1000, context=context)
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={**context, "validation_error": validation_error, "event": "output_validation_failed"}
            )
            raise ConversionError(
                validation_error or "Conversion finished but output file is invalid",
                context=context
            )

        output_size = os.path.getsize(docx_path)
        logger.info(
            "PDF to DOCX conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            }
        )

        return pdf_path, docx_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during PDF to DOCX conversion",
            extra={**context, "event": "unexpected_error", "error_type": type(e).__name__}
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__}
        ) from e
    finally:
        # Note: We don't cleanup tmp_dir here - that's handled by the view
        pass
