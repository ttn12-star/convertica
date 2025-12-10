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


def parse_pages(pages_str: str, total_pages: int) -> list[int]:
    """Parse page string into list of page indices (0-indexed).

    Args:
        pages_str: Page string like "all", "1,3,5", or "1-5"
        total_pages: Total number of pages in PDF

    Returns:
        List of 0-indexed page numbers
    """
    if pages_str.lower() == "all":
        return list(range(total_pages))

    page_indices = []
    parts = pages_str.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # Range like "1-5"
            start, end = part.split("-", 1)
            try:
                start_idx = max(0, int(start.strip()) - 1)  # Convert to 0-indexed
                end_idx = min(total_pages, int(end.strip()))  # Keep 1-indexed for range
                page_indices.extend(range(start_idx, end_idx))
            except ValueError:
                logger.warning("Invalid page range: %s", part)
        else:
            # Single page number
            try:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    page_indices.append(page_num - 1)  # Convert to 0-indexed
            except ValueError:
                logger.warning("Invalid page number: %s", part)

    return sorted(set(page_indices))  # Remove duplicates and sort


def convert_pdf_to_jpg(
    uploaded_file: UploadedFile,
    pages: str = "all",
    dpi: int = 300,  # Default 300 DPI for high quality
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF pages to JPG images and return as ZIP archive.

    Args:
        uploaded_file (UploadedFile): Uploaded PDF file.
        pages (str): Page string like "all", "1,3,5", or "1-5". Defaults to "all".
        dpi (int): DPI for image quality (72-600).
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_pdf, path_to_zip) where zip contains selected JPG images.

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
        "pages": pages,
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

            # Parse pages string to get list of pages to convert
            pages_to_convert = parse_pages(pages, total_pages)
            context["pages_to_convert"] = len(pages_to_convert)

            if not pages_to_convert:
                raise InvalidPDFError(
                    "No valid pages selected for conversion", context=context
                )
        except ImportError:
            # PyPDF2 not available, skip page validation
            logger.debug(
                "PyPDF2 not available, skipping page count validation", extra=context
            )
            # If we can't validate, convert all pages
            pages_to_convert = None
        except InvalidPDFError:
            raise
        except Exception as e:
            logger.warning(
                "Could not validate pages",
                extra={**context, "error": str(e), "event": "page_validation_warning"},
            )
            # Continue anyway - convert all pages
            pages_to_convert = None

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
            # Convert all pages first, then filter by selected pages
            try:
                # Try to convert from bytes first (more efficient)
                all_images = convert_from_bytes(
                    pdf_bytes,
                    dpi=dpi,
                    fmt="jpeg",
                )
            except Exception:
                # Fallback to path-based conversion
                logger.debug(
                    "Bytes conversion failed, trying path-based", extra=context
                )
                all_images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    fmt="jpeg",
                )

            # Filter images by selected pages (if pages_to_convert is specified)
            if pages_to_convert is not None:
                images = [
                    all_images[i] for i in pages_to_convert if i < len(all_images)
                ]
            else:
                images = all_images

            if not images or len(images) == 0:
                raise ConversionError("No images generated from PDF", context=context)

            # Create ZIP archive with all images
            # Use ZIP_STORED for better compatibility and to avoid recompression issues
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for idx, image in enumerate(images):
                    # Determine page number for filename (1-indexed for display)
                    if pages_to_convert is not None:
                        # Use the actual page number from the list
                        page_num = (
                            pages_to_convert[idx] + 1
                        )  # Convert back to 1-indexed
                    else:
                        page_num = idx + 1  # 1-indexed

                    # Save image to temporary file with maximum quality
                    # Use quality=100 for lossless-like quality, subsampling=0 to preserve color accuracy
                    jpg_name = f"{base}_page{page_num:04d}.jpg"
                    temp_jpg = os.path.join(tmp_dir, jpg_name)

                    # Convert image to RGB mode if needed (some PDFs may have different color modes)
                    if image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")

                    # Save with maximum quality and no subsampling for best quality
                    image.save(
                        temp_jpg,
                        "JPEG",
                        quality=100,  # Maximum quality
                        optimize=False,  # Disable optimization to avoid recompression
                        subsampling=0,  # No chroma subsampling for best color accuracy
                    )

                    # Verify file was saved correctly before adding to ZIP
                    if os.path.exists(temp_jpg) and os.path.getsize(temp_jpg) > 0:
                        # Add to ZIP with explicit compression
                        zipf.write(temp_jpg, jpg_name)
                        # Clean up temporary JPG
                        os.remove(temp_jpg)
                    else:
                        logger.warning(
                            "Failed to save image file",
                            extra={
                                **context,
                                "page_num": page_num,
                                "event": "image_save_failed",
                            },
                        )

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
