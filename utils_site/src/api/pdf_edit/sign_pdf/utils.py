# utils.py
import os
import tempfile

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


def _calculate_signature_rect(
    page_rect: fitz.Rect,
    position: str,
    sig_w: float,
    sig_h: float,
) -> fitz.Rect:
    """Calculate the bounding rectangle for the signature on the page.

    Args:
        page_rect: The page dimensions as a fitz.Rect (x0, y0, x1, y1).
        position: One of bottom-right, bottom-left, bottom-center,
                  top-right, top-left, center.
        sig_w: Signature width in points.
        sig_h: Signature height in points.

    Returns:
        A fitz.Rect specifying where to draw the signature.
    """
    x0, y0, x1, y1 = page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1
    margin = 20.0

    if position == "bottom-right":
        rect = fitz.Rect(
            x1 - sig_w - margin, y1 - sig_h - margin, x1 - margin, y1 - margin
        )
    elif position == "bottom-left":
        rect = fitz.Rect(
            x0 + margin, y1 - sig_h - margin, x0 + margin + sig_w, y1 - margin
        )
    elif position == "bottom-center":
        cx = (x0 + x1) / 2
        rect = fitz.Rect(
            cx - sig_w / 2, y1 - sig_h - margin, cx + sig_w / 2, y1 - margin
        )
    elif position == "top-right":
        rect = fitz.Rect(
            x1 - sig_w - margin, y0 + margin, x1 - margin, y0 + margin + sig_h
        )
    elif position == "top-left":
        rect = fitz.Rect(
            x0 + margin, y0 + margin, x0 + margin + sig_w, y0 + margin + sig_h
        )
    elif position == "center":
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        rect = fitz.Rect(cx - sig_w / 2, cy - sig_h / 2, cx + sig_w / 2, cy + sig_h / 2)
    else:
        # Default to bottom-right
        rect = fitz.Rect(
            x1 - sig_w - margin, y1 - sig_h - margin, x1 - margin, y1 - margin
        )

    return rect


def sign_pdf(
    pdf_file: UploadedFile,
    signature_image: UploadedFile,
    page_number: int = 0,
    position: str = "bottom-right",
    signature_width: int = 150,
    opacity: float = 1.0,
    all_pages: bool = False,
    suffix: str = "_signed",
) -> tuple[str, str]:
    """Add an image signature to a PDF page using PyMuPDF.

    Args:
        pdf_file: The uploaded PDF file.
        signature_image: The uploaded signature image (PNG/JPG, transparency supported).
        page_number: 0-indexed page number to sign (default 0 = first page).
        position: Where on the page to place the signature. One of:
            bottom-right, bottom-left, bottom-center, top-right, top-left, center.
        signature_width: Width of the signature in points (default 150).
        opacity: Opacity of the signature image, 0.0-1.0 (default 1.0).
        all_pages: If True, apply the signature to every page.
        suffix: Filename suffix for the output file.

    Returns:
        Tuple of (input_pdf_path, output_pdf_path).
    """
    context = {
        "function": "sign_pdf",
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

        # Save signature image bytes to temp file so fitz can read it
        sig_data = signature_image.read()
        sig_tmp_path = os.path.join(tmp_dir, "signature_img")
        with open(sig_tmp_path, "wb") as f:
            f.write(sig_data)

        # Determine natural image dimensions via fitz to compute aspect ratio
        try:
            img_doc = fitz.open(sig_tmp_path)
            # fitz.open on an image gives a single-page PDF wrapper
            img_page = img_doc[0]
            img_rect = img_page.rect
            img_natural_w = img_rect.width
            img_natural_h = img_rect.height
            img_doc.close()
        except Exception:
            # Fallback: use PIL to get dimensions
            try:
                from PIL import Image as PILImage

                with PILImage.open(sig_tmp_path) as pil_img:
                    img_natural_w, img_natural_h = pil_img.size
            except Exception:
                # If all else fails, assume square
                img_natural_w = img_natural_h = 1.0

        # Compute signature height maintaining aspect ratio
        if img_natural_w > 0:
            sig_h = signature_width * (img_natural_h / img_natural_w)
        else:
            sig_h = float(signature_width)
        sig_w = float(signature_width)

        logger.info(
            "sign_pdf: page=%d, position=%s, sig_w=%.1f, sig_h=%.1f, opacity=%.2f, all_pages=%s",
            page_number,
            position,
            sig_w,
            sig_h,
            opacity,
            all_pages,
            extra=context,
        )

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            context["total_pages"] = total_pages

            if all_pages:
                pages_to_sign = list(range(total_pages))
            else:
                # Clamp page_number to valid range
                target_page = max(0, min(page_number, total_pages - 1))
                pages_to_sign = [target_page]

            for page_idx in pages_to_sign:
                page = doc[page_idx]
                rect = _calculate_signature_rect(page.rect, position, sig_w, sig_h)

                # insert_image accepts a stream (bytes) directly
                page.insert_image(
                    rect,
                    stream=sig_data,
                    overlay=True,
                    xref=0,
                    keep_proportion=True,
                )

                # Apply opacity via graphics state if not fully opaque
                if opacity < 1.0:
                    # Draw a transparent rectangle overlay is not directly supported;
                    # use a PDF graphics state to set alpha on the image we just inserted.
                    # The cleanest way with PyMuPDF is to set the alpha when inserting.
                    # Re-insert with alpha parameter (available in newer PyMuPDF builds).
                    # We remove the last inserted image and reinsert with alpha.
                    try:
                        # Remove the previously inserted image xref and reinsert with alpha
                        page.clean_contents()
                        page.insert_image(
                            rect,
                            stream=sig_data,
                            overlay=True,
                            xref=0,
                            keep_proportion=True,
                            alpha=opacity,
                        )
                    except TypeError:
                        # Older PyMuPDF without alpha kwarg — leave as fully opaque
                        logger.debug(
                            "PyMuPDF does not support alpha kwarg for insert_image; "
                            "signature will be fully opaque.",
                            extra=context,
                        )

            doc.save(output_path, garbage=4, deflate=True)
            doc.close()

            processor.validate_output_pdf(output_path, min_size=1000)

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to sign PDF",
                extra={**error_context, "event": "sign_pdf_error"},
                exc_info=True,
            )
            raise ConversionError(
                "Failed to sign PDF: %s" % e, context=error_context
            ) from e

        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error in sign_pdf",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            "Unexpected error: %s" % e,
            context={**context, "error_type": type(e).__name__},
        ) from e
