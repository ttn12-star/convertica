"""
PDF to PowerPoint conversion utilities.

Note: This is a basic implementation that extracts PDF pages as images
and creates a PowerPoint presentation. For production use, consider using
specialized libraries or services for better quality conversion.
"""

import os
import tempfile
from collections import Counter
from io import BytesIO
from pathlib import Path

import fitz
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_pdf_file,
)
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)


_SLIDE_LONG_SIDE_IN = 10
_MAX_RENDER_PIXELS = 4000  # longest side; an A0 page at 150 DPI would be ~7000


def _dpi_for(rect) -> int:
    return int(min(150, _MAX_RENDER_PIXELS * 72 / max(rect.width, rect.height)))


def convert_pdf_to_ppt(
    uploaded_file: UploadedFile,
    extract_images: bool = True,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF to PowerPoint presentation.

    Args:
        uploaded_file: PDF file to convert
        extract_images: Whether to extract images from PDF
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)

    Raises:
        ConversionError: If conversion fails
        StorageError: If disk space is insufficient
    """
    context = {
        "function": "convert_pdf_to_ppt",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "extract_images": extract_images,
    }

    logger.info("Starting PDF to PowerPoint conversion", extra=context)

    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ModuleNotFoundError as e:
        raise ConversionError(
            "PDF to PowerPoint conversion requires 'python-pptx' to be installed."
        ) from e

    # Create temp directory
    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_ppt_")
    input_path = None
    output_path = None

    try:
        # Check disk space (estimate output ~5x input)
        required_mb = max(1, (uploaded_file.size * 5) // (1024 * 1024))
        disk_ok, disk_error = check_disk_space(tmp_dir, required_mb=required_mb)
        if not disk_ok:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        # Save uploaded file
        safe_filename = sanitize_filename(get_valid_filename(uploaded_file.name))
        input_path = os.path.join(tmp_dir, safe_filename)

        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Validate the PDF up front so a corrupt / non-PDF .pdf is a clean 400
        # instead of a generic 500 out of pdf2image (validate_pdf_pages swallows
        # parser errors, so without this it slipped through).
        is_valid, pdf_error = validate_pdf_file(input_path, context)
        if not is_valid:
            raise InvalidPDFError(pdf_error or "Invalid or corrupt PDF file.")

        logger.debug(
            "Saved PDF file",
            extra={
                **context,
                "input_path": input_path,
                "file_size": uploaded_file.size,
            },
        )

        # One page at a time: pdf2image rendered the whole document into RAM
        # first (~4 GB for 200 pages, in a web worker).
        try:
            doc = fitz.open(input_path)
        except (fitz.FileDataError, RuntimeError) as e:
            raise InvalidPDFError("Invalid or corrupt PDF file.") from e
        with doc:
            if doc.page_count == 0:
                raise ConversionError("Failed to extract pages from PDF")
            num_pages = doc.page_count

            # Slide shape follows the most common page shape; every page is
            # fitted into it without stretching (a fixed 4:3 slide distorted
            # portrait A4 1.9x, and a banner first page shrank all the rest).
            aspect = Counter(
                round(page.rect.height / page.rect.width, 2) for page in doc
            ).most_common(1)[0][0]
            prs = Presentation()
            prs.slide_width = Inches(_SLIDE_LONG_SIDE_IN)
            prs.slide_height = Inches(min(max(_SLIDE_LONG_SIDE_IN * aspect, 1), 56))
            blank_slide_layout = prs.slide_layouts[6]  # Blank layout

            for page in doc:
                pix = page.get_pixmap(dpi=_dpi_for(page.rect), alpha=False)
                image = BytesIO(pix.tobytes("jpeg", jpg_quality=90))
                del pix

                slide = prs.slides.add_slide(blank_slide_layout)
                scale = min(
                    prs.slide_width / page.rect.width,
                    prs.slide_height / page.rect.height,
                )
                width = int(page.rect.width * scale)
                height = int(page.rect.height * scale)
                slide.shapes.add_picture(
                    image,
                    (prs.slide_width - width) // 2,
                    (prs.slide_height - height) // 2,
                    width=width,
                    height=height,
                )

        logger.info(
            f"Rendered {num_pages} pages into slides",
            extra={**context, "num_pages": num_pages},
        )

        # Save PowerPoint file
        base_name = Path(safe_filename).stem
        output_filename = f"{base_name}{suffix}.pptx"
        output_path = os.path.join(tmp_dir, output_filename)

        prs.save(output_path)

        output_size = os.path.getsize(output_path)
        logger.info(
            "PDF to PowerPoint conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": output_size,
                "num_slides": num_pages,
            },
        )

        return input_path, output_path

    except InvalidPDFError:
        raise  # a 400 for the user's file, not a 500
    except Exception as e:
        logger.exception(
            "PDF to PowerPoint conversion failed",
            extra={**context, "error": str(e)},
        )
        raise ConversionError(f"Failed to convert PDF to PowerPoint: {str(e)}") from e
