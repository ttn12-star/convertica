"""Change the page size of a PDF (A4 / Letter / Legal) without cropping content.

Two things make this different from cropping or from the buyer's "fit to page"
print setting:

* Content is re-placed with ``show_pdf_page``, so text and vector art stay
  vector. Rasterising here would destroy exactly the print quality the people
  who need this tool care about.
* ``auto`` mode never loses content. A4 and Letter are different *shapes*
  (Letter is 5.9 mm wider and 17.6 mm shorter), so centring an A4 page on
  Letter at 100% silently eats 8.8 mm off the top and the bottom. So we measure
  where the ink actually is and only shrink when the ink would not fit.

One scale is computed for the whole document, never per page: a planner whose
pages were each scaled to their own content would print with the grid drifting
from sheet to sheet.
"""

import os
import tempfile
from pathlib import Path

import fitz
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from PIL import Image
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)

MM = 72 / 25.4

# Target sheets, in points. Values are the paper standards, not printer
# hardware: the unprintable edge of a home printer is the buyer's problem and
# is covered by keeping a safe margin in the design.
PAGE_SIZES = {
    "a4": (210 * MM, 297 * MM),
    "letter": (215.9 * MM, 279.4 * MM),
    "legal": (215.9 * MM, 355.6 * MM),
}

MODES = ("auto", "fit")

# Ink detection resolution. 36 dpi puts the quantisation error at ~0.7 mm and
# always in the safe direction (the measured box is never smaller than the real
# one), which is what we want when the answer decides whether to shrink.
_BBOX_DPI = 36
_WHITE_CUTOFF = 250


def _content_bbox(page: fitz.Page) -> fitz.Rect | None:
    """Bounding box of visible ink on the page, or None for a blank page.

    Measured from a low-resolution render rather than by walking page objects:
    a render treats text, vector art, images and a full-bleed background alike,
    and correctly reports a background as covering the whole page.
    """
    pixmap = page.get_pixmap(dpi=_BBOX_DPI, colorspace=fitz.csGRAY)
    image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    # Pillow's getbbox() is the C-speed version of scanning for non-white
    # pixels; a Python loop over a 40-page planner costs seconds.
    ink = image.point(lambda value: 255 if value < _WHITE_CUTOFF else 0)
    box = ink.getbbox()
    if not box:
        return None
    scale = 72 / _BBOX_DPI
    return fitz.Rect(box[0] * scale, box[1] * scale, box[2] * scale, box[3] * scale)


def _document_scale(
    boxes: list[fitz.Rect | None], target: tuple[float, float]
) -> float:
    """Largest scale <= 1.0 at which every page's ink fits the target sheet."""
    target_w, target_h = target
    scale = 1.0
    for box in boxes:
        if box is None or box.width <= 0 or box.height <= 0:
            continue
        scale = min(scale, target_w / box.width, target_h / box.height)
    return min(1.0, scale)


def _placement(
    source: fitz.Rect,
    anchor: fitz.Rect | None,
    target: tuple[float, float],
    scale: float,
) -> fitz.Rect:
    """Where to draw the source page on the target sheet.

    ``anchor`` is the ink box; centring the ink rather than the page uses the
    available room on the new sheet as well as possible. Falls back to the page
    rect on a blank page.
    """
    target_w, target_h = target
    box = anchor if anchor is not None else source
    width, height = source.width * scale, source.height * scale
    # Offset that puts the scaled ink box in the middle of the sheet.
    left = (target_w - box.width * scale) / 2 - box.x0 * scale
    top = (target_h - box.height * scale) / 2 - box.y0 * scale
    return fitz.Rect(left, top, left + width, top + height)


def resize_pdf(
    pdf_file: UploadedFile,
    target_size: str = "letter",
    mode: str = "auto",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Re-sheet a PDF onto a different paper size.

    Args:
        pdf_file: Uploaded PDF file
        target_size: One of PAGE_SIZES ("a4", "letter", "legal")
        mode: "auto" keeps 100% when the content fits and otherwise shrinks by
            the smallest amount that loses nothing; "fit" always scales the
            whole page to the sheet.
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    target_size = (target_size or "letter").lower()
    mode = (mode or "auto").lower()

    context = {
        "function": "resize_pdf",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
        "target_size": target_size,
        "mode": mode,
    }

    # Validate at the boundary: an unknown size would otherwise KeyError deep
    # inside the conversion and surface as a 500.
    if target_size not in PAGE_SIZES:
        raise InvalidPDFError(
            f"Unsupported page size '{target_size}'. "
            f"Choose one of: {', '.join(sorted(PAGE_SIZES))}.",
            context=context,
        )
    if mode not in MODES:
        raise InvalidPDFError(
            f"Unsupported mode '{mode}'. Choose one of: {', '.join(MODES)}.",
            context=context,
        )

    logger.info("Starting PDF page resize", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="resize_pdf_")
    input_path = None
    output_path = None

    try:
        required_mb = max(50, int((pdf_file.size * 3) / (1024 * 1024)))
        has_space, disk_error = check_disk_space(tmp_dir, required_mb=required_mb)
        if not has_space:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        safe_filename = sanitize_filename(get_valid_filename(pdf_file.name))
        input_path = os.path.join(tmp_dir, safe_filename)

        with open(input_path, "wb") as file_obj:
            for chunk in pdf_file.chunks():
                file_obj.write(chunk)

        is_valid, validation_error = validate_pdf_file(input_path, context)
        if not is_valid:
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        base_name = Path(safe_filename).stem
        output_path = os.path.join(tmp_dir, f"{base_name}{suffix}.pdf")

        target = PAGE_SIZES[target_size]

        try:
            source = fitz.open(input_path)
            out = fitz.open()

            # Rendering each page to find its ink is the only non-trivial cost
            # here, so do it once and reuse: the scale needs every page's box
            # before the first page can be placed.
            boxes: list[fitz.Rect | None] = (
                [_content_bbox(page) for page in source] if mode == "auto" else []
            )
            doc_scale = _document_scale(boxes, target) if mode == "auto" else None

            for index, page in enumerate(source):
                page_rect = page.rect
                new_page = out.new_page(width=target[0], height=target[1])

                if mode == "fit":
                    scale = min(
                        target[0] / page_rect.width, target[1] / page_rect.height
                    )
                    anchor = None
                else:
                    scale = doc_scale
                    anchor = boxes[index]

                new_page.show_pdf_page(
                    _placement(page_rect, anchor, target, scale), source, index
                )

            out.save(output_path, garbage=4, clean=True, deflate=True)
            out.close()
            source.close()
        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to resize PDF pages",
                extra={**error_context, "event": "resize_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to change PDF page size: {e}", context=error_context
            ) from e

        is_output_valid, output_error = validate_output_file(
            output_path,
            min_size=100,
            context=context,
        )
        if not is_output_valid:
            raise ConversionError(
                output_error or "Output file is invalid", context=context
            )

        logger.info(
            "PDF page resize completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
            },
        )
        return input_path, output_path

    except (StorageError, InvalidPDFError, ConversionError):
        raise
    except Exception as error:
        logger.exception(
            "PDF page resize failed",
            extra={**context, "error": str(error)},
        )
        raise ConversionError(
            f"Failed to change PDF page size: {error}",
            context=context,
        ) from error
