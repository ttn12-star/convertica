# utils.py
"""Signature placement utilities.

Two entry points:

* `sign_pdf()` — main entry used by the single-file endpoint. Takes a list
  of per-signature placements (page index, top-left x/y, width, height in
  PDF points, and a PNG data-URI image).

* `apply_simple_signature_to_pdf()` — legacy helper used by the batch
  endpoint. Applies a single uploaded image with an enum position to one
  or all pages. Batch keeps this contract because all files in a batch
  share the same placement.
"""
import base64
import os

import fitz  # PyMuPDF
from django.core.files.uploadedfile import UploadedFile
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)


def _decode_data_uri(data_uri: str) -> bytes:
    """Decode a `data:image/...;base64,XXXX` URI into raw bytes."""
    if ";base64," not in data_uri:
        raise ValueError("Signature image must be a base64 data URI.")
    _, b64 = data_uri.split(";base64,", 1)
    try:
        return base64.b64decode(b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Could not decode base64 signature image.") from exc


def _calculate_signature_rect(
    page_rect: fitz.Rect,
    position: str,
    sig_w: float,
    sig_h: float,
) -> fitz.Rect:
    """Build a placement rect for the legacy enum-position contract (batch only)."""
    x0, y0, x1, y1 = page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1
    margin = 20.0

    if position == "bottom-left":
        return fitz.Rect(
            x0 + margin, y1 - sig_h - margin, x0 + margin + sig_w, y1 - margin
        )
    if position == "bottom-center":
        cx = (x0 + x1) / 2
        return fitz.Rect(
            cx - sig_w / 2, y1 - sig_h - margin, cx + sig_w / 2, y1 - margin
        )
    if position == "top-right":
        return fitz.Rect(
            x1 - sig_w - margin, y0 + margin, x1 - margin, y0 + margin + sig_h
        )
    if position == "top-left":
        return fitz.Rect(
            x0 + margin, y0 + margin, x0 + margin + sig_w, y0 + margin + sig_h
        )
    if position == "center":
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        return fitz.Rect(cx - sig_w / 2, cy - sig_h / 2, cx + sig_w / 2, cy + sig_h / 2)
    # default + "bottom-right"
    return fitz.Rect(x1 - sig_w - margin, y1 - sig_h - margin, x1 - margin, y1 - margin)


def _insert_signature(
    page: fitz.Page,
    image_bytes: bytes,
    rect: fitz.Rect,
    opacity: float = 1.0,
) -> None:
    """Insert one image into a page rect; honours opacity if PyMuPDF supports it."""
    if opacity >= 1.0:
        page.insert_image(rect, stream=image_bytes, overlay=True, keep_proportion=True)
        return

    # Try the modern alpha kwarg first; fall back to fully opaque on older builds.
    try:
        page.insert_image(
            rect,
            stream=image_bytes,
            overlay=True,
            keep_proportion=True,
            alpha=opacity,
        )
    except TypeError:
        page.insert_image(rect, stream=image_bytes, overlay=True, keep_proportion=True)


def sign_pdf(
    pdf_file: UploadedFile,
    signatures: list[dict],
    suffix: str = "_signed",
    **_legacy_kwargs,
) -> tuple[str, str]:
    """Apply a list of signature placements to a PDF.

    Args:
        pdf_file: The uploaded PDF file.
        signatures: List of dicts with keys:
            page (int, 0-indexed),
            x, y, width, height (float, PDF points, top-left origin),
            image_data_uri (str, "data:image/...;base64,...").
        suffix: Output filename suffix.

    Returns:
        Tuple of (input_pdf_path, output_pdf_path).

    Raises:
        ConversionError on processing failure.
    """
    context = {
        "function": "sign_pdf",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
        "signature_count": len(signatures),
    }

    try:
        processor = BasePDFProcessor(
            pdf_file,
            tmp_prefix="sign_pdf_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()
        tmp_dir = processor.tmp_dir

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = "%s%s.pdf" % (base, suffix)
        output_path = os.path.join(tmp_dir, output_name)
        context["output_path"] = output_path

        doc = fitz.open(pdf_path)
        try:
            total_pages = len(doc)
            context["total_pages"] = total_pages

            for idx, sig in enumerate(signatures):
                page_idx = max(0, min(int(sig["page"]), total_pages - 1))
                page = doc[page_idx]

                x = float(sig["x"])
                y = float(sig["y"])
                w = float(sig["width"])
                h = float(sig["height"])

                # Clamp the rect inside the page so an out-of-bounds drop is
                # still rendered (just visibly clipped to the page).
                page_w = page.rect.width
                page_h = page.rect.height
                x = max(0.0, min(x, page_w - 1))
                y = max(0.0, min(y, page_h - 1))
                w = max(10.0, min(w, page_w - x))
                h = max(10.0, min(h, page_h - y))

                rect = fitz.Rect(x, y, x + w, y + h)

                image_bytes = _decode_data_uri(sig["image_data_uri"])
                _insert_signature(page, image_bytes, rect, opacity=1.0)

                logger.info(
                    "sign_pdf: placed sig %d on page %d at (%.1f,%.1f) %.1fx%.1f",
                    idx,
                    page_idx,
                    x,
                    y,
                    w,
                    h,
                    extra=context,
                )

            doc.save(output_path, garbage=4, deflate=True)
        finally:
            doc.close()

        processor.validate_output_pdf(output_path, min_size=1000)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except ValueError as exc:
        # Bad data URI from the client — surface as ConversionError so the
        # base view returns 400/500 with a clean message.
        logger.warning("sign_pdf: bad input — %s", exc, extra=context)
        raise ConversionError(str(exc), context=context) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in sign_pdf",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(exc).__name__,
            },
        )
        raise ConversionError(
            "Unexpected error: %s" % exc,
            context={**context, "error_type": type(exc).__name__},
        ) from exc


def apply_simple_signature_to_pdf(
    pdf_file: UploadedFile,
    signature_image: UploadedFile,
    page_number: int = 0,
    position: str = "bottom-right",
    signature_width: int = 150,
    opacity: float = 1.0,
    all_pages: bool = False,
    suffix: str = "_signed",
) -> tuple[str, str]:
    """Legacy helper kept for the batch endpoint.

    Applies a single uploaded image to one or all pages using an enum
    position. This mirrors the original `sign_pdf` contract from before
    the per-coordinate redesign and is intentionally NOT used by the
    single-file endpoint anymore.
    """
    context = {
        "function": "apply_simple_signature_to_pdf",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
        "page_number": page_number,
        "position": position,
        "signature_width": signature_width,
        "opacity": opacity,
        "all_pages": all_pages,
    }

    try:
        processor = BasePDFProcessor(
            pdf_file,
            tmp_prefix="sign_pdf_batch_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()
        tmp_dir = processor.tmp_dir

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = "%s%s.pdf" % (base, suffix)
        output_path = os.path.join(tmp_dir, output_name)

        sig_data = signature_image.read()

        # Derive aspect ratio from the bitmap so we keep proportions.
        try:
            img_doc = fitz.open(stream=sig_data, filetype="png")
            img_rect = img_doc[0].rect
            natural_w, natural_h = img_rect.width, img_rect.height
            img_doc.close()
        except Exception:
            try:
                from io import BytesIO

                from PIL import Image as PILImage

                with PILImage.open(BytesIO(sig_data)) as pil_img:
                    natural_w, natural_h = pil_img.size
            except Exception:
                natural_w = natural_h = 1.0

        sig_w = float(signature_width)
        sig_h = sig_w * (natural_h / natural_w if natural_w > 0 else 1.0)

        doc = fitz.open(pdf_path)
        try:
            total_pages = len(doc)
            pages = (
                list(range(total_pages))
                if all_pages
                else [max(0, min(page_number, total_pages - 1))]
            )
            for page_idx in pages:
                page = doc[page_idx]
                rect = _calculate_signature_rect(page.rect, position, sig_w, sig_h)
                _insert_signature(page, sig_data, rect, opacity=opacity)
            doc.save(output_path, garbage=4, deflate=True)
        finally:
            doc.close()

        processor.validate_output_pdf(output_path, min_size=1000)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error in apply_simple_signature_to_pdf",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(exc).__name__,
            },
        )
        raise ConversionError(
            "Unexpected error: %s" % exc,
            context={**context, "error_type": type(exc).__name__},
        ) from exc
