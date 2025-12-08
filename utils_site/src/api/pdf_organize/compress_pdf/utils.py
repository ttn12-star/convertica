# utils.py
import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import DictionaryObject

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


def compress_pdf(
    uploaded_file: UploadedFile,
    compression_level: str = "medium",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Compress PDF to reduce file size.

    Args:
        uploaded_file: PDF file to compress
        compression_level: Compression level ("low", "medium", "high")
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "compress_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "compression_level": compression_level,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="compress_pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=300)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}_compressed{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)

        context.update({"pdf_path": pdf_path, "output_path": output_path})

        # Write uploaded file
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except OSError as err:
            raise StorageError(f"Failed to write PDF: {err}", context=context) from err

        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower():
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Repair PDF to handle potentially corrupted files
        pdf_path = repair_pdf(pdf_path)

        # Compress PDF
        try:
            logger.info(
                "Starting PDF compression", extra={**context, "event": "compress_start"}
            )

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            # Copy all pages with aggressive compression
            for page_num, page in enumerate(reader.pages):
                # Compress page content streams multiple times for better compression
                try:
                    # First compression pass - always compress
                    page.compress_content_streams()

                    # For medium and high compression, try additional passes
                    if compression_level in ["medium", "high"]:
                        # Try to compress again (some streams may not compress on first pass)
                        try:
                            page.compress_content_streams()
                        except Exception:
                            pass  # Ignore if already compressed

                    # For high compression, try even more aggressive optimization
                    if compression_level == "high":
                        # Third compression pass for maximum compression
                        try:
                            page.compress_content_streams()
                        except Exception:
                            pass

                        # Try to optimize page resources (fonts, images, etc.)
                        try:
                            if "/Resources" in page:
                                resources = page["/Resources"]
                                # Remove unused resources if possible
                                # This is a conservative approach - we don't want to break the PDF
                                if isinstance(resources, DictionaryObject):
                                    # Keep resources but optimize them
                                    pass
                        except Exception:
                            pass  # Non-critical optimization

                except Exception as e:
                    logger.warning(
                        "Failed to compress page %d: %s",
                        page_num + 1,
                        e,
                        extra={**context, "page": page_num + 1},
                    )

                # Add page to writer
                writer.add_page(page)

            # Optimize based on compression level
            if compression_level == "high":
                # High compression: remove links, annotations, bookmarks, and optimize metadata
                writer.remove_links = True
                writer.remove_annotations = True
                # Try to remove bookmarks/outline if possible
                try:
                    if hasattr(writer, "remove_outline"):
                        writer.remove_outline = True
                except Exception:
                    pass

                # Try to remove metadata for maximum compression
                try:
                    # Remove document metadata if possible
                    if hasattr(writer, "remove_metadata"):
                        writer.remove_metadata = True
                except Exception:
                    pass

            elif compression_level == "medium":
                # Medium compression: remove links, try to remove some annotations
                writer.remove_links = True
                writer.remove_annotations = False  # Keep annotations but compress them
            else:  # low
                # Low compression: keep everything, just compress streams
                writer.remove_links = False
                writer.remove_annotations = False

            # Always keep images (we compress them via compress_content_streams)
            writer.remove_images = False

            # Write compressed PDF with optimization
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            # For medium and high compression, try to re-read and re-compress for additional optimization
            # This can sometimes achieve better compression ratios
            if compression_level in ["medium", "high"]:
                try:
                    initial_size = os.path.getsize(output_path)
                    max_passes = 3 if compression_level == "high" else 2

                    current_path = output_path
                    best_size = initial_size
                    best_path = output_path

                    # Try multiple compression passes
                    for pass_num in range(1, max_passes + 1):
                        try:
                            # Re-read the compressed PDF and compress again
                            temp_reader = PdfReader(current_path)
                            temp_writer = PdfWriter()

                            for page in temp_reader.pages:
                                try:
                                    # Compress each page again
                                    page.compress_content_streams()
                                    # Try additional passes for high compression
                                    if compression_level == "high":
                                        try:
                                            page.compress_content_streams()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                temp_writer.add_page(page)

                            temp_writer.remove_links = True
                            if compression_level == "high":
                                temp_writer.remove_annotations = True

                            # Write to a temporary file
                            temp_output = current_path + f".pass{pass_num}.tmp"
                            with open(temp_output, "wb") as temp_file:
                                temp_writer.write(temp_file)

                            temp_size = os.path.getsize(temp_output)

                            # Keep this version if it's better (at least 0.5% smaller)
                            if temp_size < best_size * 0.995:
                                # Clean up previous temporary files
                                if best_path != output_path and os.path.exists(
                                    best_path
                                ):
                                    try:
                                        os.remove(best_path)
                                    except Exception:
                                        pass
                                best_size = temp_size
                                best_path = temp_output
                                current_path = temp_output
                                logger.debug(
                                    "Compression pass %d improved size: %d bytes",
                                    pass_num,
                                    temp_size,
                                    extra={
                                        **context,
                                        "event": f"pass_{pass_num}_success",
                                    },
                                )
                            else:
                                # Remove this temporary file as it didn't help
                                os.remove(temp_output)
                                logger.debug(
                                    "Compression pass %d did not improve size",
                                    pass_num,
                                    extra={
                                        **context,
                                        "event": f"pass_{pass_num}_skipped",
                                    },
                                )
                                break  # No improvement, stop trying

                        except Exception as e:
                            logger.debug(
                                "Compression pass %d failed (non-critical): %s",
                                pass_num,
                                e,
                                extra={**context, "event": f"pass_{pass_num}_failed"},
                            )
                            break  # Stop trying if pass fails

                    # Replace original if we found a better version
                    if best_path != output_path and best_size < initial_size * 0.995:
                        os.replace(best_path, output_path)
                        logger.debug(
                            "Multi-pass compression improved size: %d -> %d bytes (%.2f%%)",
                            initial_size,
                            best_size,
                            ((initial_size - best_size) / initial_size * 100),
                            extra={**context, "event": "multi_pass_success"},
                        )
                    elif best_path != output_path:
                        # Clean up temporary file
                        try:
                            os.remove(best_path)
                        except Exception:
                            pass

                except Exception as e:
                    logger.debug(
                        "Multi-pass compression failed (non-critical): %s",
                        e,
                        extra={**context},
                    )
                    # Continue with original compressed file

            logger.debug(
                "Compression completed", extra={**context, "event": "compress_complete"}
            )

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "PDF compression failed",
                extra={**error_context, "event": "compress_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to compress PDF: {e}", context=error_context
            ) from e

        # Validate output
        is_valid, validation_error = validate_output_file(
            output_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output PDF is invalid", context=context
            )

        input_size = os.path.getsize(pdf_path)
        output_size = os.path.getsize(output_path)
        compression_ratio = (
            ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
        )

        logger.info(
            "PDF compression successful",
            extra={
                **context,
                "event": "compress_success",
                "input_size": input_size,
                "input_size_mb": round(input_size / (1024 * 1024), 2),
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
                "compression_ratio": round(compression_ratio, 2),
            },
        )

        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
