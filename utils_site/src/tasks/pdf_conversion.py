"""
Celery tasks for PDF conversion operations.

These tasks handle heavy PDF conversion operations asynchronously
to prevent blocking the main request/response cycle.
"""

import os

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from src.api.logging_utils import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True, name="pdf_conversion.convert_pdf_to_word", queue="pdf_conversion"
)
def convert_pdf_to_word_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """
    Asynchronously convert PDF to Word.

    Args:
        file_path: Path to the uploaded PDF file
        output_filename: Desired output filename
        **kwargs: Additional conversion parameters

    Returns:
        dict: Result containing output_path or error message
    """
    try:
        from src.api.pdf_convert.pdf_to_word.utils import convert_pdf_to_word

        # Read file from storage
        with default_storage.open(file_path, "rb") as f:
            uploaded_file = ContentFile(f.read())
            uploaded_file.name = os.path.basename(file_path)

        # Perform conversion
        pdf_path, docx_path = convert_pdf_to_word(uploaded_file, suffix="_convertica")

        # Store result path
        result_path = docx_path

        logger.info(f"PDF to Word conversion completed: {result_path}")

        return {
            "status": "success",
            "output_path": result_path,
            "output_filename": output_filename,
        }

    except Exception as exc:
        logger.error(f"PDF to Word conversion failed: {str(exc)}", exc_info=True)
        # Retry on failure
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task(
    bind=True, name="pdf_conversion.convert_word_to_pdf", queue="pdf_conversion"
)
def convert_word_to_pdf_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """
    Asynchronously convert Word to PDF.

    Args:
        file_path: Path to the uploaded Word file
        output_filename: Desired output filename
        **kwargs: Additional conversion parameters

    Returns:
        dict: Result containing output_path or error message
    """
    try:
        from src.api.pdf_convert.word_to_pdf.utils import convert_word_to_pdf

        # Read file from storage
        with default_storage.open(file_path, "rb") as f:
            uploaded_file = ContentFile(f.read())
            uploaded_file.name = os.path.basename(file_path)

        # Perform conversion
        docx_path, pdf_path = convert_word_to_pdf(uploaded_file, suffix="_convertica")

        logger.info(f"Word to PDF conversion completed: {pdf_path}")

        return {
            "status": "success",
            "output_path": pdf_path,
            "output_filename": output_filename,
        }

    except Exception as exc:
        logger.error(f"Word to PDF conversion failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task(bind=True, name="pdf_conversion.compress_pdf", queue="pdf_processing")
def compress_pdf_task(
    self,
    file_path: str,
    output_filename: str,
    compression_level: str = "medium",
    **kwargs,
) -> dict:
    """
    Asynchronously compress PDF.

    Args:
        file_path: Path to the uploaded PDF file
        output_filename: Desired output filename
        compression_level: Compression level (low, medium, high)
        **kwargs: Additional parameters

    Returns:
        dict: Result containing output_path, compression stats, or error message
    """
    try:
        from src.api.pdf_organize.compress_pdf.utils import compress_pdf

        # Read file from storage
        with default_storage.open(file_path, "rb") as f:
            uploaded_file = ContentFile(f.read())
            uploaded_file.name = os.path.basename(file_path)

        # Get original size
        original_size = uploaded_file.size

        # Perform compression
        pdf_path, output_path = compress_pdf(
            uploaded_file, compression_level=compression_level, suffix="_convertica"
        )

        # Get compressed size
        compressed_size = os.path.getsize(output_path)
        compression_ratio = (1 - compressed_size / original_size) * 100

        logger.info(
            f"PDF compression completed: {output_path}, "
            f"ratio: {compression_ratio:.2f}%"
        )

        return {
            "status": "success",
            "output_path": output_path,
            "output_filename": output_filename,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
        }

    except Exception as exc:
        logger.error(f"PDF compression failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60, max_retries=3)
