"""
PDF to JPG conversion utilities with parallel processing optimization.
"""

import os
import tempfile
import zipfile

from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader

from ....exceptions import ConversionError, InvalidPDFError, StorageError
from ...file_validation import check_disk_space, sanitize_filename
from ...logging_utils import get_logger
from ...optimization_manager import optimization_manager

logger = get_logger(__name__)


async def convert_pdf_to_jpg(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """
    Convert PDF to JPG using adaptive optimization.

    Args:
        uploaded_file: Uploaded PDF file
        suffix: Suffix for output filename
    """
    return await optimization_manager.convert_pdf_to_jpg(uploaded_file, suffix=suffix)


async def convert_pdf_to_jpg_sequential(
    uploaded_file: UploadedFile,
    pages: str = "all",
    dpi: int = 300,
    suffix: str = "_convertica",
    tmp_dir: str = None,
    context: dict = None,
) -> tuple[str, str]:
    """Sequential PDF to JPG conversion (fallback implementation)."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="pdf2jpg_")

    if context is None:
        context = {}

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))

    # Save uploaded file
    pdf_path = os.path.join(tmp_dir, safe_name)
    with open(pdf_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Create ZIP for JPG files
    base_name = os.path.splitext(safe_name)[0]
    zip_name = f"{base_name}{suffix}.zip"
    zip_path = os.path.join(tmp_dir, zip_name)

    try:
        # Read PDF
        with open(pdf_path, "rb") as f:
            pdf_reader = PdfReader(f)
            total_pages = len(pdf_reader.pages)

        # Determine which pages to convert
        if pages == "all":
            page_indices = list(range(total_pages))
        elif "-" in pages:
            # Range like "1-5"
            start, end = map(int, pages.split("-"))
            page_indices = list(range(start - 1, min(end, total_pages)))
        else:
            # Single page
            page_idx = int(pages) - 1
            if 0 <= page_idx < total_pages:
                page_indices = [page_idx]
            else:
                page_indices = []

        if not page_indices:
            raise InvalidPDFError(f"No valid pages found for pages={pages}")

        # Convert pages to images
        images = []
        for page_idx in page_indices:
            try:
                page = pdf_reader.pages[page_idx]

                # Convert page to image (simplified version)
                # In real implementation, you'd use pdf2image or similar
                image_data = page.render_to_image(dpi=dpi)

                # Save image
                image_name = f"page_{page_idx + 1}.jpg"
                image_path = os.path.join(tmp_dir, image_name)
                image_data.save(image_path, "JPEG", quality=85)
                images.append(image_path)

            except Exception as e:
                logger.warning(f"Failed to convert page {page_idx + 1}: {e}")
                continue

        if not images:
            raise ConversionError("No pages could be converted to images")

        # Create ZIP archive
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for image_path in images:
                zipf.write(image_path, os.path.basename(image_path))

        return pdf_path, zip_path

    except Exception as e:
        # Cleanup on error
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise

    finally:
        # Cleanup temporary images
        for page_idx in page_indices:
            image_path = os.path.join(tmp_dir, f"page_{page_idx + 1}.jpg")
            if os.path.exists(image_path):
                os.remove(image_path)
