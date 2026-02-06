import os
from collections.abc import Callable

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger
from ...pdf_processing import BasePDFMultiProcessor
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def merge_pdf(
    uploaded_files: list[UploadedFile],
    order: str = "upload",
    suffix: str = "_convertica",
    check_cancelled: Callable[[], None] | None = None,
    **kwargs,
) -> tuple[str, str]:
    """Merge multiple PDF files into one.

    Args:
        uploaded_files: List of PDF files to merge
        order: Merge order ("upload" or "alphabetical")
        suffix: Suffix for output filename

    Returns:
        Tuple of (temp_dir, output_path)
    """
    context = {
        "function": "merge_pdf",
        "num_files": len(uploaded_files),
        "order": order,
    }

    try:
        # Sort files if needed
        if order == "alphabetical":
            uploaded_files = sorted(uploaded_files, key=lambda f: f.name)

        processor = BasePDFMultiProcessor(
            uploaded_files,
            tmp_prefix="merge_pdf_",
            required_mb=500,
            context=context,
        )
        pdf_paths = processor.prepare()
        tmp_dir = processor.tmp_dir

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

            def _open_reader(path: str) -> PdfReader:
                try:
                    return PdfReader(path, strict=False)
                except Exception:
                    repaired = repair_pdf(path)
                    return PdfReader(repaired, strict=False)

            for idx, pdf_path in enumerate(pdf_paths):
                # Check cancellation before processing each file
                if callable(check_cancelled):
                    check_cancelled()

                try:
                    reader = _open_reader(pdf_path)

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

                    for page_num, page in enumerate(reader.pages):
                        # Check cancellation periodically (every 10 pages)
                        if page_num % 10 == 0 and callable(check_cancelled):
                            check_cancelled()

                        try:
                            writer.add_page(page)
                        except Exception as page_err:
                            raise InvalidPDFError(
                                "Failed to read page %d from PDF %d (%s)"
                                % (
                                    page_num + 1,
                                    idx + 1,
                                    os.path.basename(pdf_path),
                                ),
                                context={
                                    **context,
                                    "pdf_index": idx + 1,
                                    "page_num": page_num + 1,
                                    "error": str(page_err)[:200],
                                },
                            ) from page_err

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
            except OSError as write_err:
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

        processor.validate_output_pdf(output_path, min_size=1000)

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
