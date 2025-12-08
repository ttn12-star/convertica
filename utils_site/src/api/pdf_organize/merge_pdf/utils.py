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

        # Save all files
        pdf_paths = []
        for idx, uploaded_file in enumerate(uploaded_files):
            safe_name = sanitize_filename(
                f"{idx}_{os.path.basename(uploaded_file.name)}"
            )
            pdf_path = os.path.join(tmp_dir, safe_name)

            try:
                with open(pdf_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                # Validate each PDF
                is_valid, validation_error = validate_pdf_file(pdf_path, context)
                if not is_valid:
                    if "password" in (validation_error or "").lower():
                        raise EncryptedPDFError(
                            f"PDF {safe_name} is password-protected", context=context
                        )
                    raise InvalidPDFError(f"Invalid PDF: {safe_name}", context=context)

                pdf_paths.append(pdf_path)
            except (OSError, IOError) as err:
                raise StorageError(
                    f"Failed to write PDF {safe_name}: {err}", context=context
                ) from err

        # Merge PDFs
        try:
            logger.info("Starting PDF merge", extra={**context, "event": "merge_start"})

            writer = PdfWriter()

            for idx, pdf_path in enumerate(pdf_paths):
                try:
                    # Try to read PDF with strict=False for better compatibility
                    reader = PdfReader(pdf_path, strict=False)

                    # Check if PDF is encrypted
                    if reader.is_encrypted:
                        logger.warning(
                            f"PDF {idx + 1} is encrypted, attempting to decrypt",
                            extra={**context, "pdf_index": idx + 1},
                        )
                        # Try to decrypt with empty password (common case)
                        if not reader.decrypt(""):
                            raise EncryptedPDFError(
                                f"PDF {idx + 1} is password-protected and cannot be decrypted",
                                context=context,
                            )

                    # Add all pages from this PDF
                    num_pages = len(reader.pages)
                    for page_num, page in enumerate(reader.pages):
                        try:
                            writer.add_page(page)
                        except Exception as page_err:
                            logger.warning(
                                f"Failed to add page {page_num + 1} from PDF {idx + 1}: {page_err}",
                                extra={
                                    **context,
                                    "pdf_index": idx + 1,
                                    "page_num": page_num + 1,
                                    "error": str(page_err),
                                },
                            )
                            # Continue with next page instead of failing completely
                            continue

                    logger.debug(
                        f"Added {num_pages} pages from PDF {idx + 1}",
                        extra={**context, "pdf_index": idx + 1, "num_pages": num_pages},
                    )

                except EncryptedPDFError:
                    raise
                except Exception as pdf_err:
                    error_msg = str(pdf_err)
                    logger.error(
                        f"Failed to read PDF {idx + 1}: {error_msg}",
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
                        f"Failed to read PDF {idx + 1}: {error_msg}",
                        context=context,
                    ) from pdf_err

            # Check if any pages were added
            if len(writer.pages) == 0:
                raise ConversionError(
                    "No pages were added to merged PDF. All input PDFs may be invalid or empty.",
                    context=context,
                )

            # Generate output filename
            first_name = sanitize_filename(os.path.basename(uploaded_files[0].name))
            base = os.path.splitext(first_name)[0]
            output_name = f"{base}_merged{suffix}.pdf"
            output_path = os.path.join(tmp_dir, output_name)

            # Write merged PDF
            try:
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
            except (OSError, IOError) as write_err:
                raise StorageError(
                    f"Failed to write merged PDF: {write_err}",
                    context=context,
                ) from write_err

            logger.debug(
                f"Merge completed: {len(writer.pages)} pages merged",
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
                f"Failed to merge PDFs: {merge_exc}", context=error_context
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
            f"Unexpected error: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
