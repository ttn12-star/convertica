"""
PDF to JPG conversion utilities with parallel processing optimization.
"""

import os
import shutil
import tempfile
import zipfile
from collections.abc import Callable

from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import UploadedFile

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from ....exceptions import ConversionError, InvalidPDFError, StorageError
from ...file_validation import check_disk_space, sanitize_filename
from ...logging_utils import get_logger
from ...optimization_manager import optimization_manager

logger = get_logger(__name__)


def convert_pdf_to_jpg(
    uploaded_file: UploadedFile,
    pages: str = "all",
    dpi: int = 300,
    suffix: str = "_convertica",
    tmp_dir: str | None = None,
    context: dict | None = None,
    check_cancelled: Callable[[], None] | None = None,
) -> tuple[str, str]:
    """
    Convert PDF to JPG using adaptive optimization.

    Args:
        uploaded_file: Uploaded PDF file
        pages: Pages to convert ('all', '1', '1-5')
        dpi: Output DPI
        suffix: Suffix for output filename
        tmp_dir: Optional temp directory to write files into
        context: Optional logging context
    """
    return async_to_sync(optimization_manager.convert_pdf_to_jpg)(
        uploaded_file,
        pages=pages,
        dpi=dpi,
        suffix=suffix,
        tmp_dir=tmp_dir,
        context=context,
        check_cancelled=check_cancelled,
    )


def convert_pdf_to_jpg_sequential(
    uploaded_file: UploadedFile,
    pages: str = "all",
    dpi: int = 300,
    suffix: str = "_convertica",
    tmp_dir: str = None,
    context: dict = None,
    check_cancelled: Callable[[], None] | None = None,
) -> tuple[str, str]:
    """Sequential PDF to JPG conversion (fallback implementation)."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="pdf2jpg_")

    if context is None:
        context = {}

    disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=200)
    if not disk_ok:
        raise StorageError(disk_err or "Insufficient disk space", context=context)

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))

    pdf_path = os.path.join(tmp_dir, safe_name)
    with open(pdf_path, "wb") as f:
        for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
            if callable(check_cancelled):
                check_cancelled()
            f.write(chunk)

    # Create ZIP for JPG files
    base_name = os.path.splitext(safe_name)[0]
    zip_name = f"{base_name}{suffix}.zip"
    zip_path = os.path.join(tmp_dir, zip_name)

    page_indices: list[int] = []

    try:
        parse_context = {
            **context,
            "file_name": safe_name,
            "file_size": getattr(uploaded_file, "size", None),
        }

        try:
            with open(pdf_path, "rb") as f:
                pdf_reader = PdfReader(f)
                total_pages = len(pdf_reader.pages)
        except Exception as e:
            logger.warning("Failed to parse PDF for page count: %s", e)
            raise InvalidPDFError(
                "Invalid or corrupted PDF file", context=parse_context
            ) from e

        if total_pages == 0:
            raise InvalidPDFError("PDF file has no pages")

        # Determine which pages to convert
        if pages == "all":
            page_indices = list(range(total_pages))
        elif "-" in pages:
            # Range like "1-5"
            start, end = map(int, pages.split("-"))
            page_indices = list(range(start - 1, min(end, total_pages)))
        else:
            # Single page
            page_num = int(pages) - 1
            if 0 <= page_num < total_pages:
                page_indices = [page_num]
            else:
                page_indices = []

        if not page_indices:
            raise InvalidPDFError(f"No valid pages found for pages={pages}")

        # Fast PDF to JPG conversion using pdf2image
        try:
            from pdf2image import convert_from_path

            first_page = page_indices[0] + 1
            last_page = page_indices[-1] + 1

            thread_count = 1
            try:
                thread_count = max(
                    1,
                    min(
                        2,
                        int(
                            getattr(optimization_manager, "config", {})
                            .get("thread_workers", {})
                            .get("image", 1)
                        ),
                    ),
                )
            except Exception:
                thread_count = 1

            # Use paths_only to avoid holding large PIL images in memory
            image_paths = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=first_page,
                last_page=last_page,
                fmt="jpeg",
                output_folder=tmp_dir,
                paths_only=True,
                thread_count=thread_count,
                use_pdftocairo=True,
            )

            images = []
            for i, src_path in enumerate(image_paths):
                if callable(check_cancelled):
                    check_cancelled()
                page_num = page_indices[i] + 1
                dst_path = os.path.join(tmp_dir, f"page_{page_num}.jpg")
                if src_path != dst_path:
                    try:
                        os.replace(src_path, dst_path)
                    except OSError:
                        shutil.copy2(src_path, dst_path)
                        try:
                            os.remove(src_path)
                        except OSError:
                            pass
                images.append(dst_path)

        except ImportError:
            # Fallback: create placeholder images
            logger.warning("pdf2image not available, using placeholder images")
            images = []
            for page_idx in page_indices:
                if callable(check_cancelled):
                    check_cancelled()
                try:
                    from PIL import Image, ImageDraw, ImageFont

                    img_size = (
                        int(8.27 * dpi),
                        int(11.69 * dpi),
                    )  # A4 size at given DPI
                    image = Image.new("RGB", img_size, color="white")
                    draw = ImageDraw.Draw(image)

                    try:
                        font = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48
                        )
                    except OSError:
                        font = ImageFont.load_default()

                    text = f"Page {page_idx + 1}"
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (img_size[0] - text_width) // 2
                    y = (img_size[1] - text_height) // 2
                    draw.text((x, y), text, fill="black", font=font)

                    image_name = f"page_{page_idx + 1}.jpg"
                    image_path = os.path.join(tmp_dir, image_name)
                    image.save(image_path, "JPEG", quality=85)
                    images.append(image_path)

                except Exception as e:
                    logger.warning(
                        f"Failed to create placeholder for page {page_idx + 1}: {e}"
                    )
                    continue
        except Exception as e:
            logger.error(f"pdf2image conversion failed: {e}")
            # Fallback to placeholder images
            images = []
            for page_idx in page_indices:
                if callable(check_cancelled):
                    check_cancelled()
                try:
                    from PIL import Image, ImageDraw, ImageFont

                    img_size = (int(8.27 * dpi), int(11.69 * dpi))
                    image = Image.new("RGB", img_size, color="white")
                    draw = ImageDraw.Draw(image)

                    try:
                        font = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48
                        )
                    except OSError:
                        font = ImageFont.load_default()

                    text = f"Page {page_idx + 1}"
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (img_size[0] - text_width) // 2
                    y = (img_size[1] - text_height) // 2
                    draw.text((x, y), text, fill="black", font=font)

                    image_name = f"page_{page_idx + 1}.jpg"
                    image_path = os.path.join(tmp_dir, image_name)
                    image.save(image_path, "JPEG", quality=85)
                    images.append(image_path)

                except Exception as e2:
                    logger.warning(
                        f"Failed to create placeholder for page {page_idx + 1}: {e2}"
                    )
                    continue

        if not images:
            raise ConversionError("No pages could be converted to images")

        # Create ZIP archive
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for image_path in images:
                if callable(check_cancelled):
                    check_cancelled()
                zipf.write(image_path, os.path.basename(image_path))

        return pdf_path, zip_path

    except Exception:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise

    finally:
        # Cleanup temporary images
        for page_idx in page_indices:
            image_path = os.path.join(tmp_dir, f"page_{page_idx + 1}.jpg")
            if os.path.exists(image_path):
                os.remove(image_path)
