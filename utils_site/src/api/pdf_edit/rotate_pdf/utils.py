import os

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor
from ...pdf_utils import parse_pages

logger = get_logger(__name__)


def rotate_pdf(
    uploaded_file: UploadedFile,
    angle: int = 90,
    pages: str = "all",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Rotate PDF pages by specified angle.

    Args:
        uploaded_file: PDF file to rotate
        angle: Rotation angle in degrees (90, 180, or 270)
        pages: Pages to rotate ("all", "1,3,5", or "1-5")
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)

    Raises:
        ConversionError, StorageError, InvalidPDFError, EncryptedPDFError
    """
    context = {
        "function": "rotate_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "angle": angle,
        "pages": pages,
    }

    try:
        # Validate angle
        if angle not in [90, 180, 270]:
            raise ConversionError(
                "Rotation angle must be 90, 180, or 270 degrees", context=context
            )

        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="rotate_pdf_",
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
            pages_to_rotate: set[int],
            angle: int,
        ):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                if page_num in pages_to_rotate:
                    page.rotate(angle)
                writer.add_page(page)
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        reader_probe = PdfReader(pdf_path)
        total_pages = len(reader_probe.pages)
        pages_to_rotate = set(parse_pages(pages, total_pages))
        context["total_pages"] = total_pages
        context["pages_to_rotate"] = len(pages_to_rotate)

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            pages_to_rotate=pages_to_rotate,
            angle=angle,
        )
        processor.validate_output_pdf(output_path, min_size=1000)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during PDF rotation",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error during rotation: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
