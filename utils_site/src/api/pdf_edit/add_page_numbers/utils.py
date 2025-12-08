# utils.py
import os
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

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


def get_page_position(
    position: str, page_width: float, page_height: float, font_size: int
):
    """Calculate x, y coordinates for page number based on position."""
    margin = 0.5 * inch

    if "top" in position:
        y = page_height - margin - font_size
    else:  # bottom
        y = margin

    if "left" in position:
        x = margin
    elif "right" in position:
        x = page_width - margin - (font_size * 2)  # Approximate width
    else:  # center
        x = page_width / 2

    return x, y


def add_page_numbers(
    uploaded_file: UploadedFile,
    position: str = "bottom-center",
    font_size: int = 12,
    start_number: int = 1,
    format_str: str = "{page}",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Add page numbers to PDF.

    Args:
        uploaded_file: PDF file
        position: Position of page numbers
        font_size: Font size for numbers
        start_number: Starting page number
        format_str: Format string (e.g., "{page} of {total}")
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "add_page_numbers",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "position": position,
        "font_size": font_size,
        "start_number": start_number,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="add_pages_")
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
            logger.debug(
                "Writing PDF file", extra={**context, "event": "file_write_start"}
            )
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except OSError as err:
            raise StorageError(
                f"Failed to write PDF: {err}",
                context={**context, "error_type": type(err).__name__},
            ) from err

        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if (
                "password" in (validation_error or "").lower()
                or "encrypted" in (validation_error or "").lower()
            ):
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Repair PDF to handle potentially corrupted files
        pdf_path = repair_pdf(pdf_path)

        # Add page numbers
        try:
            logger.info(
                "Adding page numbers", extra={**context, "event": "add_numbers_start"}
            )

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            for page_num in range(total_pages):
                page = reader.pages[page_num]

                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                # Create overlay with page number
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))

                # Calculate position
                x, y = get_page_position(position, page_width, page_height, font_size)

                # Format page number text
                page_number = start_number + page_num
                text = format_str.format(page=page_number, total=total_pages)

                # Draw page number
                can.setFont("Helvetica", font_size)
                can.drawString(x, y, text)
                can.save()

                # Merge overlay with original page
                packet.seek(0)
                overlay = PdfReader(packet)
                overlay_page = overlay.pages[0]

                page.merge_page(overlay_page)
                writer.add_page(page)

            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.debug(
                "Page numbers added", extra={**context, "event": "add_numbers_complete"}
            )

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to add page numbers",
                extra={**error_context, "event": "add_numbers_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to add page numbers: {e}", context=error_context
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
            "Page numbers added successfully",
            extra={
                **context,
                "event": "add_numbers_success",
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
