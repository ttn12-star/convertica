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


def extract_pages(
    uploaded_file: UploadedFile, pages: str, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Extract specific pages from PDF.

    Args:
        uploaded_file: PDF file
        pages: Pages to extract (comma-separated or ranges)
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "extract_pages",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "pages": pages,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="extract_pages_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = f"{base}_extracted{suffix}.pdf"
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _op(input_pdf_path: str, *, output_path: str, pages_to_extract: list[int]):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            for page_num in pages_to_extract:
                writer.add_page(reader.pages[page_num])
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        reader_probe = PdfReader(pdf_path)
        total_pages = len(reader_probe.pages)
        pages_to_extract = parse_pages(pages, total_pages)

        context["total_pages"] = total_pages
        context["pages_to_extract"] = len(pages_to_extract)

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            pages_to_extract=pages_to_extract,
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
