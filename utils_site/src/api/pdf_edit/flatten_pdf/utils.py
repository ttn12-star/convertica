"""Flatten PDF utilities - removes interactive form fields and annotations."""

import os
from pathlib import Path

import fitz
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)


def flatten_pdf(
    pdf_file: UploadedFile,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Flatten PDF by removing interactive form fields and annotations.

    Args:
        pdf_file: Uploaded PDF file
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "flatten_pdf",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
    }

    logger.info("Starting PDF flatten", extra=context)

    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="flatten_pdf_")
    input_path = None
    output_path = None

    try:
        required_mb = max(50, int((pdf_file.size * 3) / (1024 * 1024)))
        has_space, disk_error = check_disk_space(tmp_dir, required_mb=required_mb)
        if not has_space:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        safe_filename = sanitize_filename(get_valid_filename(pdf_file.name))
        input_path = os.path.join(tmp_dir, safe_filename)

        with open(input_path, "wb") as file_obj:
            for chunk in pdf_file.chunks():
                file_obj.write(chunk)

        is_valid, validation_error = validate_pdf_file(input_path, context)
        if not is_valid:
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        base_name = Path(safe_filename).stem
        output_filename = f"{base_name}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_filename)

        try:
            doc = fitz.open(input_path)
            for page in doc:
                # Flatten content streams
                page.clean_contents()
                # Remove widget annotations (form fields)
                widgets = list(page.widgets())
                for widget in widgets:
                    page.delete_widget(widget)
                # Remove other annotations
                annots = list(page.annots())
                for annot in annots:
                    page.delete_annot(annot)

            doc.save(
                output_path,
                garbage=4,
                clean=True,
                deflate=True,
            )
            doc.close()
        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to flatten PDF",
                extra={**error_context, "event": "flatten_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to flatten PDF: {e}", context=error_context
            ) from e

        is_output_valid, output_error = validate_output_file(
            output_path,
            min_size=100,
            context=context,
        )
        if not is_output_valid:
            raise ConversionError(
                output_error or "Output file is invalid", context=context
            )

        logger.info(
            "PDF flatten completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
            },
        )
        return input_path, output_path

    except (StorageError, InvalidPDFError, ConversionError):
        raise
    except Exception as error:
        logger.exception(
            "PDF flatten failed",
            extra={**context, "error": str(error)},
        )
        raise ConversionError(
            f"Failed to flatten PDF: {error}",
            context=context,
        ) from error
