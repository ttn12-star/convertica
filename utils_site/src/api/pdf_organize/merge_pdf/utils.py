# utils.py
import os
import tempfile
from typing import List, Tuple

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
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


def merge_pdf(
    uploaded_files: List[UploadedFile],
    order: str = "upload",
    suffix: str = "_convertica",
) -> Tuple[str, str]:
    """Merge multiple PDF files into one.

    Args:
        uploaded_files: List of PDF files to merge
        order: Merge order ("upload" or "alphabetical")
        suffix: Suffix for output filename

    Returns:
        Tuple of (temp_dir, output_path)
    """
    tmp_dir = None
    context = {
        "function": "merge_pdf",
        "num_files": len(uploaded_files),
        "order": order,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="merge_pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=500)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        # Sort files if needed
        if order == "alphabetical":
            uploaded_files = sorted(uploaded_files, key=lambda f: f.name)

        # Save all files in order
        pdf_paths = []
        logger.info(
            "Saving %d files for merge",
            len(uploaded_files),
            extra={
                **context,
                "file_names": [f.name for f in uploaded_files],
            },
        )

        for idx, uploaded_file in enumerate(uploaded_files):
            safe_name = sanitize_filename(
                "%d_%s" % (idx, os.path.basename(uploaded_file.name))
            )
            pdf_path = os.path.join(tmp_dir, safe_name)

            logger.debug(
                "Saving file %d: %s -> %s",
                idx + 1,
                uploaded_file.name,
                safe_name,
                extra={**context, "file_index": idx + 1},
            )

            try:
                with open(pdf_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                # Validate each PDF
                is_valid, validation_error = validate_pdf_file(pdf_path, context)
                if not is_valid:
                    if "password" in (validation_error or "").lower():
                        raise EncryptedPDFError(
                            "PDF %s is password-protected" % safe_name, context=context
                        )
                    raise InvalidPDFError(
                        "Invalid PDF: %s" % safe_name, context=context
                    )

                # Repair PDF to handle potentially corrupted files
                pdf_path = repair_pdf(pdf_path)
                pdf_paths.append(pdf_path)
                logger.debug(
                    "File %d saved successfully: %s",
                    idx + 1,
                    safe_name,
                    extra={**context, "file_index": idx + 1, "pdf_path": pdf_path},
                )
            except (OSError, IOError) as err:
                raise StorageError(
                    "Failed to write PDF %s: %s" % (safe_name, err), context=context
                ) from err

        # Merge PDFs
        try:
            logger.info(
                "Starting PDF merge",
                extra={
                    **context,
                    "event": "merge_start",
                    "num_files": len(pdf_paths),
                    "file_paths": pdf_paths,
                },
            )

            writer = PdfWriter()
            total_pages_added = 0

            for idx, pdf_path in enumerate(pdf_paths):
                try:
                    # Try to read PDF with strict=False for better compatibility
                    reader = PdfReader(pdf_path, strict=False)

                    # Check if PDF is encrypted
                    if reader.is_encrypted:
                        logger.warning(
                            "PDF %d is encrypted, attempting to decrypt",
                            idx + 1,
                            extra={**context, "pdf_index": idx + 1},
                        )
                        # Try to decrypt with empty password (common case)
                        if not reader.decrypt(""):
                            raise EncryptedPDFError(
                                "PDF %d is password-protected and cannot be decrypted"
                                % (idx + 1),
                                context=context,
                            )

                    # Add all pages from this PDF
                    pages_added_from_this_pdf = 0
                    for page_num, page in enumerate(reader.pages):
                        try:
                            writer.add_page(page)
                            pages_added_from_this_pdf += 1
                            total_pages_added += 1
                        except Exception as page_err:
                            logger.warning(
                                "Failed to add page %d from PDF %d: %s",
                                page_num + 1,
                                idx + 1,
                                page_err,
                                extra={
                                    **context,
                                    "pdf_index": idx + 1,
                                    "page_num": page_num + 1,
                                    "error": str(page_err),
                                },
                            )
                            # Continue with next page instead of failing completely
                            continue

                    logger.info(
                        "Added %d pages from PDF %d (%s)",
                        pages_added_from_this_pdf,
                        idx + 1,
                        os.path.basename(pdf_path),
                        extra={
                            **context,
                            "pdf_index": idx + 1,
                            "num_pages": pages_added_from_this_pdf,
                            "pdf_path": pdf_path,
                        },
                    )

                except EncryptedPDFError:
                    raise
                except Exception as pdf_err:
                    error_msg = str(pdf_err)
                    logger.error(
                        "Failed to read PDF %d: %s",
                        idx + 1,
                        error_msg,
                        extra={
                            **context,
                            "pdf_index": idx + 1,
                            "pdf_path": pdf_path,
                            "error_type": type(pdf_err).__name__,
                            "error_message": error_msg,
                        },
                        exc_info=True,
                    )
                    raise InvalidPDFError(
                        "Failed to read PDF %d: %s" % (idx + 1, error_msg),
                        context=context,
                    ) from pdf_err

            # Check if any pages were added
            total_pages = len(writer.pages)
            if total_pages == 0:
                raise ConversionError(
                    "No pages were added to merged PDF. All input PDFs may be invalid or empty.",
                    context=context,
                )

            logger.info(
                "Successfully merged %d PDFs into %d pages",
                len(pdf_paths),
                total_pages,
                extra={
                    **context,
                    "num_input_files": len(pdf_paths),
                    "total_pages": total_pages,
                },
            )

            # Generate output filename
            first_name = sanitize_filename(os.path.basename(uploaded_files[0].name))
            base = os.path.splitext(first_name)[0]
            output_name = "%s_merged%s.pdf" % (base, suffix)
            output_path = os.path.join(tmp_dir, output_name)

            # Write merged PDF
            try:
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
            except (OSError, IOError) as write_err:
                raise StorageError(
                    "Failed to write merged PDF: %s" % write_err,
                    context=context,
                ) from write_err

            logger.debug(
                "Merge completed: %d pages merged",
                len(writer.pages),
                extra={
                    **context,
                    "event": "merge_complete",
                    "total_pages": len(writer.pages),
                },
            )

        except Exception as merge_exc:
            error_context = {
                **context,
                "error_type": type(merge_exc).__name__,
                "error_message": str(merge_exc),
            }
            logger.error(
                "PDF merge failed",
                extra={**error_context, "event": "merge_error"},
                exc_info=True,
            )
            raise ConversionError(
                "Failed to merge PDFs: %s" % merge_exc, context=error_context
            ) from merge_exc

        # Validate output
        is_valid, validation_error = validate_output_file(
            output_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output PDF is invalid", context=context
            )

        output_size = os.path.getsize(output_path)
        logger.info(
            "PDF merge successful",
            extra={
                **context,
                "event": "merge_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return tmp_dir, output_path

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
            "Unexpected error: %s" % e,
            context={**context, "error_type": type(e).__name__},
        ) from e
