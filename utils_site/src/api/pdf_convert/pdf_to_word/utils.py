# services/convert.py
import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from pdf2docx import Converter
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


def convert_pdf_to_docx(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
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

        disk_check, disk_error = check_disk_space(
            tmp_dir, required_mb=200
        )  # 200 MB for safety
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        logger.debug(
            "Created temporary directory",
            extra={**context, "event": "temp_dir_created"},
        )

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        docx_name = f"{base}{suffix}.docx"
        docx_path = os.path.join(tmp_dir, docx_name)

        context.update(
            {
                "pdf_path": pdf_path,
                "docx_path": docx_path,
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

        # Perform conversion with optimized parameters
        try:
            logger.info(
                "Starting PDF to DOCX conversion",
                extra={**context, "event": "conversion_start"},
            )

            # Optimization: Skip repair for clean PDFs to save time (major speed improvement)
            # repair_pdf can be very slow for image-heavy files (5-10x slower, adds minutes for large files)
            # Try conversion directly first, only repair if it fails
            conversion_pdf_path = pdf_path
            repair_attempted = False

            try:
                # Check if PDF is image-heavy (optimization)
                # Image-heavy PDFs benefit from lower resolution conversion
                import fitz  # PyMuPDF

                doc = fitz.open(conversion_pdf_path)
                total_images = sum(len(page.get_images()) for page in doc)
                total_pages = len(doc)
                images_per_page = total_images / max(total_pages, 1)
                doc.close()

                # If more than 3 images per page on average, it's image-heavy
                is_image_heavy = images_per_page > 3

                logger.debug(
                    "PDF analysis",
                    extra={
                        **context,
                        "total_images": total_images,
                        "total_pages": total_pages,
                        "images_per_page": round(images_per_page, 2),
                        "is_image_heavy": is_image_heavy,
                    },
                )

                # First attempt: direct conversion without repair
                cv = Converter(conversion_pdf_path)
                try:
                    # Convert with settings optimized for speed and quality
                    # For image-heavy PDFs, use lower resolution to speed up conversion
                    # (users care more about speed than perfect image quality)
                    cv.convert(
                        docx_path,
                        start=0,  # Start from first page
                        end=None,  # Convert all pages
                        pages=None,  # Convert all pages
                        image_dir=None,  # Embed images in DOCX (faster than extracting separately)
                    )
                    # Note: pdf2docx library automatically tries to preserve page breaks
                    # by detecting page boundaries in the PDF and inserting page breaks in DOCX
                    logger.debug(
                        "Conversion completed (direct, no repair needed)",
                        extra={
                            **context,
                            "event": "conversion_complete",
                            "repaired": False,
                        },
                    )
                finally:
                    cv.close()
            except Exception as first_attempt_error:
                # First attempt failed - try with repair
                logger.warning(
                    "Direct conversion failed, attempting with PDF repair",
                    extra={
                        **context,
                        "event": "retry_with_repair",
                        "first_error": str(first_attempt_error)[:200],
                    },
                )
                repair_attempted = True

                # Repair the PDF
                repaired_pdf_path = os.path.join(tmp_dir, f"repaired_{safe_name}")
                conversion_pdf_path = repair_pdf(pdf_path, repaired_pdf_path)

                # Second attempt with repaired PDF
                cv = Converter(conversion_pdf_path)
                try:
                    cv.convert(
                        docx_path,
                        start=0,
                        end=None,
                        pages=None,
                        image_dir=None,
                    )
                    logger.debug(
                        "Conversion completed (with repair)",
                        extra={
                            **context,
                            "event": "conversion_complete",
                            "repaired": True,
                        },
                    )
                finally:
                    cv.close()

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

            # Check for corrupted xref/object reference errors
            if any(
                keyword in msg
                for keyword in ["object out of range", "xref", "out of range"]
            ):
                logger.warning(
                    "PDF has corrupted object references",
                    extra={**error_context, "event": "corrupted_xref_error"},
                )
                raise InvalidPDFError(
                    "PDF file is corrupted (invalid object references). "
                    "Please try re-saving the PDF from the original application.",
                    context=error_context,
                ) from conv_exc

            # Check for scanned PDF (no extractable text)
            if (
                any(
                    keyword in msg
                    for keyword in [
                        "words count: 0",
                        "no text",
                        "scanned",
                        "image",
                        "no extractable text",
                    ]
                )
                or "words count" in msg.lower()
            ):
                logger.warning(
                    "Scanned PDF detected (no extractable text)",
                    extra={**error_context, "event": "scanned_pdf_detected"},
                )
                raise InvalidPDFError(
                    "This PDF appears to be a scanned document (image-based) and does not contain extractable text. "
                    "PDF to Word conversion requires text-based PDFs. Please use OCR software to extract text from scanned PDFs first.",
                    context=error_context,
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
                "PDF conversion failed",
                extra={**error_context, "event": "conversion_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Conversion failed: {conv_exc}", context=error_context
            ) from conv_exc

        # Validate output file
        is_valid, validation_error = validate_output_file(
            docx_path, min_size=1000, context=context
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

        output_size = os.path.getsize(docx_path)
        logger.info(
            "PDF to DOCX conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return pdf_path, docx_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during PDF to DOCX conversion",
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
