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
    from pypdf import PdfReader

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

        # Determine which pages to convert. Malformed user input ("1-", "-5",
        # "1-5-9", "abc", "0-3") must yield a clean 4xx, not an uncaught
        # ValueError → 500, and must not index page -1.
        if pages == "all":
            page_indices = list(range(total_pages))
        elif "-" in pages:
            parts = pages.split("-")
            if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit()):
                raise InvalidPDFError(f"Invalid page range: {pages}")
            start, end = int(parts[0]), int(parts[1])
            start = max(start, 1)  # clamp so start-1 never goes to index -1
            page_indices = list(range(start - 1, min(end, total_pages)))
        else:
            # Single page
            if not pages.isdigit():
                raise InvalidPDFError(f"Invalid page number: {pages}")
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

        except ImportError as e:
            logger.error("pdf2image not available: %s", e)
            raise ConversionError(
                "PDF to JPG conversion requires pdf2image and Poppler to be installed."
            ) from e
        except Exception as e:
            logger.error(f"pdf2image conversion failed: {e}")
            raise ConversionError(f"Failed to convert PDF pages to images: {e}") from e

        if not images:
            # pdf2image returned an empty list WITHOUT raising. This happens when
            # poppler's own page count (pdfinfo) disagrees with pypdf's: the
            # first_page/last_page range — derived above from pypdf's total_pages
            # — gets clamped down to poppler's count, collapses to empty, and
            # convert_from_path silently returns [] (pdf2image.py:172-173). The
            # file is one poppler cannot rasterize (malformed / unsupported), not
            # a transient system fault. Raise InvalidPDFError so the Celery task
            # classifies it as user input (_is_user_input_error) and does NOT
            # retry — retrying a deterministically-unrenderable PDF only
            # amplified the same failure into Sentry (CONVERTICA-5D).
            raise InvalidPDFError(
                "The PDF could not be rendered to images. It may be invalid, "
                "corrupted, or use unsupported features — try re-saving it "
                "(Print to PDF) and upload again.",
                context=parse_context,
            )

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
