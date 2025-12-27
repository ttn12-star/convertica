import os
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

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

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
    context = {
        "function": "add_page_numbers",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "position": position,
        "font_size": font_size,
        "start_number": start_number,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="add_pages_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = f"{base}{suffix}.pdf"
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _op(
            input_pdf_path: str,
            *,
            output_path: str,
            position: str,
            font_size: int,
            start_number: int,
            format_str: str,
        ):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)

            for page_num in range(total_pages):
                page = reader.pages[page_num]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                x, y = get_page_position(position, page_width, page_height, font_size)

                page_number = start_number + page_num
                text = format_str.format(page=page_number, total=total_pages)

                can.setFont("Helvetica", font_size)
                can.drawString(x, y, text)
                can.save()

                packet.seek(0)
                overlay = PdfReader(packet)
                page.merge_page(overlay.pages[0])
                writer.add_page(page)

            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            position=position,
            font_size=font_size,
            start_number=start_number,
            format_str=format_str,
        )
        processor.validate_output_pdf(output_path, min_size=1000)
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
