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
    context = {
        "function": "remove_pages",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "pages": pages,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="remove_pages_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = f"{base}{suffix}.pdf"
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _op(input_pdf_path: str, *, output_path: str, pages_to_remove: set[int]):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            for page_num in range(total_pages):
                if page_num not in pages_to_remove:
                    writer.add_page(reader.pages[page_num])
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        reader_probe = PdfReader(pdf_path)
        total_pages = len(reader_probe.pages)
        pages_to_remove = set(parse_pages(pages, total_pages))
        context["total_pages"] = total_pages
        context["pages_to_remove"] = len(pages_to_remove)

        if len(pages_to_remove) >= total_pages:
            raise ConversionError(
                "Cannot remove all pages from PDF. At least one page must remain.",
                context=context,
            )

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            pages_to_remove=pages_to_remove,
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
