import os
import tempfile
import zipfile

from django.core.files.uploadedfile import UploadedFile
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from ...logging_utils import get_logger
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def convert_pdf_to_jpg(
    uploaded_file: UploadedFile,
    page: int = None,
    dpi: int = 300,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF pages to JPG images and return as ZIP archive.

    Args:
        uploaded_file (UploadedFile): Uploaded PDF file.
        page (int, optional): Page number to convert (1-indexed). If None, converts all pages.
        dpi (int): DPI for image quality (72-600).
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_pdf, path_to_zip) where zip contains all JPG images.

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

        disk_check, disk_error = check_disk_space(
            tmp_dir, required_mb=500
        )  # 500 MB for images
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        logger.debug(
            "Created temporary directory",
            extra={**context, "event": "temp_dir_created"},
        )

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        zip_name = f"{base}{suffix}.zip"
        zip_path = os.path.join(tmp_dir, zip_name)

        context.update(
            {
                "pdf_path": pdf_path,
                "zip_path": zip_path,
            }
        )

        # Write uploaded file to temp
        try:
            logger.debug(
                "Writing uploaded file to temporary location",
                extra={**context, "event": "file_write_start"},
            )
            with open(pdf_path, "wb") as f:
                bytes_written = 0
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
                    bytes_written += len(chunk)
            context["bytes_written"] = bytes_written
            logger.debug(
                "File written successfully",
                extra={**context, "event": "file_write_success"},
            )
        except OSError as io_err:
            logger.error(
                "Failed to write uploaded file",
                extra={**context, "event": "file_write_error", "error": str(io_err)},
                exc_info=True,
            )
            raise StorageError(
                f"Failed to write uploaded file: {io_err}",
                context={**context, "error_type": type(io_err).__name__},
            ) from io_err

        # Validate PDF file before conversion
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if (
                "password" in validation_error.lower()
                or "encrypted" in validation_error.lower()
            ):
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Get total page count
        total_pages = None
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            # If specific page requested, validate it
            if page is not None:
                if page > total_pages:
                    raise InvalidPDFError(
                        f"Page {page} does not exist. PDF has only {total_pages} page(s).",
                        context={**context, "total_pages": total_pages},
                    )
                if page < 1:
                    raise InvalidPDFError(
                        f"Page number must be 1 or greater. Got: {page}",
                        context=context,
                    )
        except ImportError:
            # PyPDF2 not available, skip page validation
            logger.debug(
                "PyPDF2 not available, skipping page count validation", extra=context
            )
        except InvalidPDFError:
            raise
        except Exception as e:
            logger.warning(
                "Could not validate page number",
                extra={**context, "error": str(e), "event": "page_validation_warning"},
            )
            # Continue anyway

        # Repair PDF to handle potentially corrupted files
        pdf_path = repair_pdf(pdf_path)

        # Perform conversion
        try:
            logger.info(
                "Starting PDF to JPG conversion",
                extra={**context, "event": "conversion_start"},
            )

            # Read PDF file
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # Convert PDF pages to images
            # If page is specified, convert only that page; otherwise convert all pages
            try:
                # Try to convert from bytes first (more efficient)
                if page is not None:
                    images = convert_from_bytes(
                        pdf_bytes,
                        dpi=dpi,
                        first_page=page,
                        last_page=page,
                        fmt="jpeg",
                    )
                else:
                    # Convert all pages
                    images = convert_from_bytes(
                        pdf_bytes,
                        dpi=dpi,
                        fmt="jpeg",
                    )
            except Exception:
                # Fallback to path-based conversion
                logger.debug(
                    "Bytes conversion failed, trying path-based", extra=context
                )
                if page is not None:
                    images = convert_from_path(
                        pdf_path,
                        dpi=dpi,
                        first_page=page,
                        last_page=page,
                        fmt="jpeg",
                    )
                else:
                    images = convert_from_path(
                        pdf_path,
                        dpi=dpi,
                        fmt="jpeg",
                    )

            if not images or len(images) == 0:
                raise ConversionError("No images generated from PDF", context=context)

            # Create ZIP archive with all images
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for idx, image in enumerate(images, start=1):
                    # Determine page number for filename
                    if page is not None:
                        page_num = page
                    else:
                        page_num = idx

                    # Save image to temporary file
                    jpg_name = f"{base}_page{page_num:04d}.jpg"
                    temp_jpg = os.path.join(tmp_dir, jpg_name)
                    image.save(temp_jpg, "JPEG", quality=95, optimize=True)

                    # Add to ZIP
                    zipf.write(temp_jpg, jpg_name)

                    # Clean up temporary JPG
                    os.remove(temp_jpg)

            context["images_count"] = len(images)
            logger.debug(
                "Conversion completed",
                extra={**context, "event": "conversion_complete"},
            )

        except Exception as conv_exc:
            msg = str(conv_exc).lower()
            error_context = {
                **context,
                "error_type": type(conv_exc).__name__,
                "error_message": str(conv_exc),
            }

            # Enhanced error detection
            if any(
                keyword in msg
                for keyword in ["encrypted", "password", "security", "permission"]
            ):
                logger.warning(
                    "PDF is encrypted/password protected",
                    extra={**error_context, "event": "encrypted_pdf_error"},
                )
                raise EncryptedPDFError(
                    "PDF is encrypted/password protected", context=error_context
                ) from conv_exc

            if any(
                keyword in msg
                for keyword in [
                    "error",
                    "parse",
                    "format",
                    "corrupt",
                    "invalid",
                    "malformed",
                ]
            ):
                logger.warning(
                    "Invalid PDF structure detected",
                    extra={**error_context, "event": "invalid_pdf_error"},
                )
                raise InvalidPDFError(
                    f"Invalid PDF structure: {conv_exc}", context=error_context
                ) from conv_exc

            logger.error(
                "PDF to JPG conversion failed",
                extra={**error_context, "event": "conversion_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Conversion failed: {conv_exc}", context=error_context
            ) from conv_exc

        # Validate output file
        is_valid, validation_error = validate_output_file(
            zip_path, min_size=1000, context=context
        )
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={
                    **context,
                    "validation_error": validation_error,
                    "event": "output_validation_failed",
                },
            )
            raise ConversionError(
                validation_error or "Conversion finished but output file is invalid",
                context=context,
            )

        output_size = os.path.getsize(zip_path)
        logger.info(
            "PDF to JPG conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
                "pages_converted": len(images) if "images_count" in context else None,
            },
        )

        return pdf_path, zip_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during PDF to JPG conversion",
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
    finally:
        # Note: We don't cleanup tmp_dir here - that's handled by the view
        pass
