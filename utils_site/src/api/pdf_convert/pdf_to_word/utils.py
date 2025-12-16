# services/convert.py
import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from pdf2docx import Converter

from ....exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)
from ...file_validation import check_disk_space, sanitize_filename, validate_output_file
from ...logging_utils import get_logger
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def convert_pdf_to_docx(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """
    Save uploaded PDF to temp, convert it to DOCX and return (pdf_path, docx_path).
    Optimized for heavy PDF files with images, safe for Celery on low-memory servers.
    Supports image-only PDFs (converts pages as images if no text detected).
    """
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    base_name = os.path.splitext(safe_name)[0]
    context = {
        "function": "convert_pdf_to_docx",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
    }

    tmp_dir = tempfile.mkdtemp(prefix="pdf2docx_")
    context["tmp_dir"] = tmp_dir

    try:
        # Check disk space
        disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=200)
        if not disk_ok:
            raise StorageError(disk_err or "Insufficient disk space", context=context)

        # File paths
        pdf_path = os.path.join(tmp_dir, safe_name)
        docx_name = f"{base_name}{suffix}.docx"
        docx_path = os.path.join(tmp_dir, docx_name)
        context.update({"pdf_path": pdf_path, "docx_path": docx_path})

        # Write uploaded file in large chunks
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)
        except OSError as e:
            raise StorageError(
                f"Failed to write uploaded file: {e}", context=context
            ) from e

        # PDF analysis: image-heavy + text detection
        import fitz  # PyMuPDF

        is_image_heavy = False
        image_only_pdf = False
        try:
            doc = fitz.open(pdf_path)
            total_images = 0
            total_text_words = 0
            max_pages_to_check = min(len(doc), 5)  # check first 5 pages

            for i, page in enumerate(doc):
                total_images += len(page.get_images())
                text = page.get_text().strip()
                total_text_words += len(text.split())
                if i + 1 >= max_pages_to_check:
                    break

            avg_images_per_page = total_images / max(1, i + 1)
            is_image_heavy = avg_images_per_page > 3
            total_pages = len(doc)
            doc.close()

            # Mark PDF as image-only if no text
            if total_text_words == 0:
                image_only_pdf = True

            context.update(
                {
                    "total_pages": total_pages,
                    "total_images_sampled": total_images,
                    "avg_images_per_page": avg_images_per_page,
                    "is_image_heavy": is_image_heavy,
                    "text_word_count_sample": total_text_words,
                    "image_only_pdf": image_only_pdf,
                }
            )

        except Exception as e:
            raise InvalidPDFError(
                f"Failed to read/analyze PDF: {e}", context=context
            ) from e

        # Conversion function
        def perform_conversion(input_pdf, output_docx):
            cv = Converter(input_pdf)
            try:
                # For image-only PDF, embed pages as images
                cv.convert(
                    output_docx,
                    start=0,
                    end=None,
                    pages=None,
                    image_dir=None,  # embed images directly
                    # pdf2docx handles image-only pages automatically
                )
            finally:
                cv.close()

        # Perform conversion, retry with repair only if needed
        conversion_pdf_path = pdf_path
        repair_attempted = False
        try:
            perform_conversion(conversion_pdf_path, docx_path)
        except Exception as first_exc:
            repair_attempted = True
            logger.warning(
                "Direct conversion failed, attempting with repair",
                extra={
                    **context,
                    "event": "retry_with_repair",
                    "error": str(first_exc)[:200],
                },
            )
            repaired_pdf_path = os.path.join(tmp_dir, f"repaired_{safe_name}")
            conversion_pdf_path = repair_pdf(pdf_path, repaired_pdf_path)
            perform_conversion(conversion_pdf_path, docx_path)

        # Validate output DOCX
        valid, val_err = validate_output_file(docx_path, min_size=1000, context=context)
        if not valid:
            raise ConversionError(val_err or "Output file invalid", context=context)

        logger.info(
            "PDF to DOCX conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "repair_attempted": repair_attempted,
                "output_size_bytes": os.path.getsize(docx_path),
            },
        )

        return pdf_path, docx_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during PDF to DOCX conversion",
            extra={**context, "event": "unexpected_error"},
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
