# utils.py
import os
import tempfile

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
from ...pdf_edit.rotate_pdf.utils import parse_pages
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def remove_pages(
    uploaded_file: UploadedFile, pages: str, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Remove pages from PDF.

    Args:
        uploaded_file: PDF file
        pages: Pages to remove (comma-separated or ranges)
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "remove_pages",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "pages": pages,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="remove_pages_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}{suffix}.pdf"
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

        # Remove pages
        try:
            logger.info(
                "Removing pages from PDF",
                extra={**context, "event": "remove_pages_start"},
            )

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            total_pages = len(reader.pages)
            pages_to_remove = parse_pages(pages, total_pages)

            context["total_pages"] = total_pages
            context["pages_to_remove"] = len(pages_to_remove)

            for page_num in range(total_pages):
                if page_num not in pages_to_remove:
                    writer.add_page(reader.pages[page_num])

            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.debug(
                "Pages removed", extra={**context, "event": "remove_pages_complete"}
            )

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to remove pages",
                extra={**error_context, "event": "remove_pages_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to remove pages: {e}", context=error_context
            ) from e

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
            "Pages removed successfully",
            extra={
                **context,
                "event": "remove_pages_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
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
