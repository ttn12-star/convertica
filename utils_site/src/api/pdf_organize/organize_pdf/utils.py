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

logger = get_logger(__name__)


def organize_pdf(
    uploaded_file: UploadedFile,
    operation: str = "reorder",
    page_order: list = None,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """General PDF organization function.

    Args:
        uploaded_file: PDF file
        operation: Type of operation ('reorder' or 'sort')
        page_order: List of page indices in desired order (0-based). If None, keeps original order.
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "organize_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "operation": operation,
        "page_order": page_order,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="organize_pdf_",
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
            operation: str,
            page_order: list | None,
        ):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)

            if operation == "reorder" and page_order:
                if len(page_order) != total_pages:
                    raise ValueError(
                        f"page_order length ({len(page_order)}) doesn't match PDF page count ({total_pages})"
                    )
                if not all(0 <= idx < total_pages for idx in page_order):
                    raise ValueError("page_order contains invalid page indices")
                if len(set(page_order)) != len(page_order):
                    raise ValueError("page_order contains duplicate page indices")
                for page_idx in page_order:
                    writer.add_page(reader.pages[page_idx])
            else:
                for page in reader.pages:
                    writer.add_page(page)

            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            operation=operation,
            page_order=page_order,
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
