# utils.py
import os
import tempfile
import zipfile

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...file_validation import check_disk_space, sanitize_filename, validate_pdf_file
from ...logging_utils import get_logger
from ...pdf_utils import repair_pdf

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
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "split_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "split_type": split_type,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="split_pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=500)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]

        # Write uploaded file
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except OSError as err:
            raise StorageError(f"Failed to write PDF: {err}", context=context) from err

        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower():
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Optimization: Skip repair for speed (PyMuPDF/pypdf handles most PDFs)
        # Uncomment if users report corrupted PDF issues: pdf_path = repair_pdf(pdf_path)

        # Split PDF
        try:
            logger.info("Starting PDF split", extra={**context, "event": "split_start"})

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            output_files = []

            if split_type == "page":
                # Split by individual pages
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
                        output_name = f"{base}_page_{page_num + 1}{suffix}.pdf"
                        output_path = os.path.join(tmp_dir, output_name)
                        with open(output_path, "wb") as f:
                            writer.write(f)
                        output_files.append(output_path)

            elif split_type == "range":
                # Split by page ranges
                if not pages:
                    raise ConversionError(
                        "Pages parameter required for range split", context=context
                    )

                ranges = pages.split(",")
                for idx, range_str in enumerate(ranges):
                    if "-" in range_str:
                        start, end = range_str.split("-", 1)
                        start_page = max(0, int(start.strip()) - 1)
                        end_page = min(total_pages, int(end.strip()))
                        writer = PdfWriter()
                        for page_num in range(start_page, end_page):
                            writer.add_page(reader.pages[page_num])
                        output_name = f"{base}_range_{idx + 1}{suffix}.pdf"
                        output_path = os.path.join(tmp_dir, output_name)
                        with open(output_path, "wb") as f:
                            writer.write(f)
                        output_files.append(output_path)

            elif split_type == "every_n":
                # Split every N pages
                n = int(pages) if pages else 1
                if n < 1:
                    n = 1

                file_idx = 1
                writer = PdfWriter()
                for page_num in range(total_pages):
                    writer.add_page(reader.pages[page_num])
                    if (page_num + 1) % n == 0 or page_num == total_pages - 1:
                        output_name = f"{base}_part_{file_idx}{suffix}.pdf"
                        output_path = os.path.join(tmp_dir, output_name)
                        with open(output_path, "wb") as f:
                            writer.write(f)
                        output_files.append(output_path)
                        writer = PdfWriter()
                        file_idx += 1

            if not output_files:
                raise ConversionError("No output files created", context=context)

            # Create ZIP file with all split PDFs
            zip_name = f"{base}_split{suffix}.zip"
            zip_path = os.path.join(tmp_dir, zip_name)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for output_file in output_files:
                    zipf.write(output_file, os.path.basename(output_file))

            logger.debug(
                "Split completed",
                extra={
                    **context,
                    "event": "split_complete",
                    "num_files": len(output_files),
                },
            )

        except Exception as split_exc:
            error_context = {
                **context,
                "error_type": type(split_exc).__name__,
                "error_message": str(split_exc),
            }
            logger.error(
                "PDF split failed",
                extra={**error_context, "event": "split_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to split PDF: {split_exc}", context=error_context
            ) from split_exc

        return tmp_dir, zip_path

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
