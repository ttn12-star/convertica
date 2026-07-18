import os
from io import BytesIO

from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...font_utils import register_unicode_font
from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)


def get_page_position(
    position: str, page_width: float, page_height: float, font_size: int
):
    """Return (x, y, anchor) for the page number.

    ``anchor`` is left/center/right so the caller can use the matching
    reportlab draw call — the old code left-anchored everything at ``width/2``
    (so "center" wasn't centred) and guessed the right-edge width as
    ``font_size*2`` (long labels overflowed the page)."""
    margin = 0.5 * inch

    if "top" in position:
        y = page_height - margin - font_size
    else:  # bottom
        y = margin

    if "left" in position:
        return margin, y, "left"
    if "right" in position:
        return page_width - margin, y, "right"
    return page_width / 2, y, "center"


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
            font_regular, _ = register_unicode_font()

            for page_num in range(total_pages):
                page = reader.pages[page_num]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                x, y, anchor = get_page_position(
                    position, page_width, page_height, font_size
                )

                page_number = start_number + page_num
                # Explicit replace (not str.format) so an unexpected token can
                # never trigger format-string injection or a runtime error; the
                # serializer already whitelists placeholders as a clean 400.
                text = format_str.replace("{page}", str(page_number)).replace(
                    "{total}", str(total_pages)
                )

                # Unicode font so localized formats ("Страница {page}") render
                # instead of tofu; anchor-aware draw so center/right are correct.
                can.setFont(font_regular, font_size)
                if anchor == "center":
                    can.drawCentredString(x, y, text)
                elif anchor == "right":
                    can.drawRightString(x, y, text)
                else:
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
