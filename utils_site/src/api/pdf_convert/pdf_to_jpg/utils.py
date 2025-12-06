import os
import tempfile
from typing import Tuple

from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
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


def convert_pdf_to_jpg(
    uploaded_file: UploadedFile,
    page: int = 1,
    dpi: int = 300,
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Convert PDF page to JPG image.

    Args:
        uploaded_file (UploadedFile): Uploaded PDF file.
        page (int): Page number to convert (1-indexed).
        dpi (int): DPI for image quality (72-600).
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_pdf, path_to_jpg) where jpg exists.

    Raises:
        EncryptedPDFError: when the PDF is password-protected.
        InvalidPDFError: when pdf is malformed and conversion fails.
        StorageError: for filesystem I/O errors.
        ConversionError: for other conversion-related failures.
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "convert_pdf_to_jpg",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "page": page,
        "dpi": dpi,
    }

    try:
        # Check disk space
        tmp_dir = tempfile.mkdtemp(prefix="pdf2jpg_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=500)  # 500 MB for images
        if not disk_check:
            raise StorageError(
                disk_error or "Insufficient disk space",
                context=context
            )
        
        logger.debug("Created temporary directory", extra={**context, "event": "temp_dir_created"})

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        jpg_name = f"{base}{suffix}_page{page}.jpg"
        jpg_path = os.path.join(tmp_dir, jpg_name)

        context.update({
            "pdf_path": pdf_path,
            "jpg_path": jpg_path,
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

        # Check page number is valid
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            if page > total_pages:
                raise InvalidPDFError(
                    f"Page {page} does not exist. PDF has only {total_pages} page(s).",
                    context={**context, "total_pages": total_pages}
                )
            if page < 1:
                raise InvalidPDFError(
                    f"Page number must be 1 or greater. Got: {page}",
                    context=context
                )
            context["total_pages"] = total_pages
        except ImportError:
            # PyPDF2 not available, skip page validation
            logger.debug("PyPDF2 not available, skipping page count validation", extra=context)
        except Exception as e:
            logger.warning(
                "Could not validate page number",
                extra={**context, "error": str(e), "event": "page_validation_warning"}
            )
            # Continue anyway

        # Perform conversion
        try:
            logger.info(
                "Starting PDF to JPG conversion",
                extra={**context, "event": "conversion_start"}
            )
            
            # Read PDF file
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            # Convert PDF page to image
            # pdf2image can work with bytes or path
            try:
                # Try to convert from bytes first (more efficient)
                images = convert_from_bytes(
                    pdf_bytes,
                    dpi=dpi,
                    first_page=page,
                    last_page=page,
                    fmt='jpeg',
                )
            except Exception:
                # Fallback to path-based conversion
                logger.debug("Bytes conversion failed, trying path-based", extra=context)
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=page,
                    last_page=page,
                    fmt='jpeg',
                )
            
            if not images or len(images) == 0:
                raise ConversionError(
                    f"No image generated for page {page}",
                    context=context
                )
            
            # Get the first (and only) image
            image = images[0]
            
            # Save as JPG with high quality
            image.save(jpg_path, 'JPEG', quality=95, optimize=True)
            
            logger.debug("Conversion completed", extra={**context, "event": "conversion_complete"})
            
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
                "PDF to JPG conversion failed",
                extra={**error_context, "event": "conversion_error"},
                exc_info=True
            )
            raise ConversionError(
                f"Conversion failed: {conv_exc}",
                context=error_context
            ) from conv_exc

        # Validate output file
        is_valid, validation_error = validate_output_file(jpg_path, min_size=1000, context=context)
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={**context, "validation_error": validation_error, "event": "output_validation_failed"}
            )
            raise ConversionError(
                validation_error or "Conversion finished but output file is invalid",
                context=context
            )

        output_size = os.path.getsize(jpg_path)
        # Get image dimensions
        try:
            with Image.open(jpg_path) as img:
                width, height = img.size
                context["image_width"] = width
                context["image_height"] = height
        except Exception:
            pass
        
        logger.info(
            "PDF to JPG conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            }
        )

        return pdf_path, jpg_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during PDF to JPG conversion",
            extra={**context, "event": "unexpected_error", "error_type": type(e).__name__}
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__}
        ) from e
    finally:
        # Note: We don't cleanup tmp_dir here - that's handled by the view
        pass

