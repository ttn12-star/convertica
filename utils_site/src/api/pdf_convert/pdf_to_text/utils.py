"""PDF to Text conversion utilities."""

from __future__ import annotations

import os
import tempfile
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


def convert_pdf_to_text(
    pdf_file: UploadedFile,
    include_page_numbers: bool = False,
    preserve_layout: bool = False,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Extract plain text from a PDF file.

    Args:
        pdf_file: Uploaded PDF file
        include_page_numbers: Add page number dividers between pages
        preserve_layout: Try to preserve text layout/columns
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path) where output_path is a .txt file
    """
    context = {
        "function": "convert_pdf_to_text",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
        "include_page_numbers": include_page_numbers,
        "preserve_layout": preserve_layout,
    }

    logger.info("Starting PDF to Text conversion", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_text_")
    input_path = None
    output_path = None

    try:
        required_mb = max(50, int((pdf_file.size * 4) / (1024 * 1024)))
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

        try:
            doc = fitz.open(input_path)
            text_parts = []

            for i, page in enumerate(doc):
                if preserve_layout:
                    text = page.get_text("text")
                else:
                    text = page.get_text()

                if include_page_numbers:
                    text_parts.append(f"--- Page {i + 1} ---\n{text}")
                else:
                    text_parts.append(text)

            doc.close()
            full_text = "\n\n".join(text_parts)
        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to extract text from PDF",
                extra={**error_context, "event": "extraction_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to extract text from PDF: {e}", context=error_context
            ) from e

        base_name = Path(safe_filename).stem
        output_filename = f"{base_name}{suffix}.txt"
        output_path = os.path.join(tmp_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(full_text)

        is_output_valid, output_error = validate_output_file(
            output_path,
            min_size=0,
            context=context,
        )
        if not is_output_valid:
            raise ConversionError(
                output_error or "Output file is invalid", context=context
            )

        logger.info(
            "PDF to Text conversion completed",
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
            "PDF to Text conversion failed",
            extra={**context, "error": str(error)},
        )
        raise ConversionError(
            f"Failed to convert PDF to Text: {error}",
            context=context,
        ) from error
