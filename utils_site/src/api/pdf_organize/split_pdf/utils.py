import os
import zipfile
from io import BytesIO

import fitz
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


def split_pdf(
    uploaded_file: UploadedFile,
    split_type: str = "page",
    pages: str = None,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Split PDF into multiple files.

    Args:
        uploaded_file: PDF file to split
        split_type: Type of split ('page', 'range', 'every_n')
        pages: Pages specification based on split_type
        suffix: Suffix for output filenames

    Returns:
        Tuple of (temp_dir, zip_path) containing split PDFs
    """
    context = {
        "function": "split_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "split_type": split_type,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="split_pdf_",
            required_mb=500,
            context=context,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        zip_name = f"{base}_split{suffix}.zip"
        zip_path = os.path.join(processor.tmp_dir, zip_name)
        context["zip_path"] = zip_path

        def _op(
            input_pdf_path: str, *, zip_path: str, split_type: str, pages: str | None
        ):
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise ConversionError("PDF has no pages", context=context)

            def _writer_to_bytes(writer: PdfWriter) -> bytes:
                buf = BytesIO()
                writer.write(buf)
                return buf.getvalue()

            written = 0
            # First attempt with PyPDF2
            with zipfile.ZipFile(
                zip_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                if split_type == "page":
                    if pages:
                        page_nums = [
                            int(p.strip()) - 1
                            for p in pages.split(",")
                            if p.strip().isdigit()
                        ]
                    else:
                        page_nums = list(range(total_pages))

                    for page_num in page_nums:
                        if 0 <= page_num < total_pages:
                            writer = PdfWriter()
                            writer.add_page(reader.pages[page_num])
                            name = f"{base}_page_{page_num + 1}{suffix}.pdf"
                            zipf.writestr(name, _writer_to_bytes(writer))
                            written += 1

                elif split_type == "range":
                    if not pages:
                        raise ConversionError(
                            "Pages parameter required for range split", context=context
                        )
                    ranges = pages.split(",")
                    for idx, range_str in enumerate(ranges):
                        if "-" not in range_str:
                            continue
                        start, end = range_str.split("-", 1)
                        start_page = max(0, int(start.strip()) - 1)
                        end_page = min(total_pages, int(end.strip()))
                        writer = PdfWriter()
                        for page_num in range(start_page, end_page):
                            writer.add_page(reader.pages[page_num])
                        name = f"{base}_range_{idx + 1}{suffix}.pdf"
                        zipf.writestr(name, _writer_to_bytes(writer))
                        written += 1

                elif split_type == "every_n":
                    n = int(pages) if pages else 1
                    if n < 1:
                        n = 1
                    file_idx = 1
                    writer = PdfWriter()
                    for page_num in range(total_pages):
                        writer.add_page(reader.pages[page_num])
                        if (page_num + 1) % n == 0 or page_num == total_pages - 1:
                            name = f"{base}_part_{file_idx}{suffix}.pdf"
                            zipf.writestr(name, _writer_to_bytes(writer))
                            written += 1
                            writer = PdfWriter()
                            file_idx += 1
                else:
                    raise ConversionError("Invalid split_type", context=context)

            # Fallback to PyMuPDF splitting if PyPDF2 produced nothing
            if written == 0:
                logger.warning(
                    "PyPDF2 produced no output, falling back to PyMuPDF",
                    extra={**context, "event": "fallback_to_pymupdf"},
                )
                doc = None
                try:
                    doc = fitz.open(input_pdf_path)
                    with zipfile.ZipFile(
                        zip_path, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zipf:
                        for page_idx in range(doc.page_count):
                            single = None
                            try:
                                single = fitz.open()
                                single.insert_pdf(
                                    doc, from_page=page_idx, to_page=page_idx
                                )
                                name = f"{base}_page_{page_idx + 1}{suffix}.pdf"
                                zipf.writestr(name, single.tobytes())
                                written += 1
                            finally:
                                if single:
                                    single.close()
                except Exception as e:
                    raise ConversionError(
                        f"No output files created (fallback failed: {e})",
                        context=context,
                    )
                finally:
                    if doc:
                        doc.close()

            if written == 0:
                raise ConversionError("No output files created", context=context)

            return zip_path

        processor.run_pdf_operation_with_repair(
            _op,
            zip_path=zip_path,
            split_type=split_type,
            pages=pages,
        )

        # ZIP is not a PDF; validate existence/size only
        from ...file_validation import validate_output_file

        is_valid, validation_error = validate_output_file(
            zip_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output ZIP is invalid", context=context
            )

        return processor.tmp_dir, zip_path

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
