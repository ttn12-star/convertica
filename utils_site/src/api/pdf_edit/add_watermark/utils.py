# utils.py
import os
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from ...logging_utils import get_logger
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)

# Register Unicode font for watermark text (supports Cyrillic, etc.)
_WATERMARK_FONT_REGISTERED = False


def _register_watermark_font():
    """Register Unicode font for watermark text rendering."""
    global _WATERMARK_FONT_REGISTERED
    if _WATERMARK_FONT_REGISTERED:
        return

    # Try to find and register a Unicode font
    unicode_font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]

    font_registered = False
    for font_path in unicode_font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("WatermarkFont", font_path))
                # Try to register bold version
                bold_path = font_path.replace("Regular", "Bold").replace(
                    "-Regular", "-Bold"
                )
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("WatermarkFontBold", bold_path))
                else:
                    # Use regular font as bold if bold version not found
                    pdfmetrics.registerFont(TTFont("WatermarkFontBold", font_path))
                logger.debug("Registered Unicode font: %s", font_path)
                font_registered = True
                break
            except Exception as e:
                logger.warning("Failed to register font %s: %s", font_path, e)
                continue

    if not font_registered:
        logger.warning(
            "No Unicode font found, using default Helvetica (may not support Cyrillic)"
        )

    _WATERMARK_FONT_REGISTERED = True


def parse_pages(pages_str: str, total_pages: int) -> list[int]:
    """Parse page string into list of page indices (0-indexed).

    Args:
        pages_str: Page string like "all", "1,3,5", or "1-5"
        total_pages: Total number of pages in PDF

    Returns:
        List of 0-indexed page numbers
    """
    if pages_str.lower() == "all":
        return list(range(total_pages))

    page_indices = []
    parts = pages_str.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # Range like "1-5"
            start, end = part.split("-", 1)
            try:
                start_idx = max(0, int(start.strip()) - 1)  # Convert to 0-indexed
                end_idx = min(total_pages, int(end.strip()))  # Keep 1-indexed for range
                page_indices.extend(range(start_idx, end_idx))
            except ValueError:
                logger.warning("Invalid page range: %s", part)
        else:
            # Single page number
            try:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    page_indices.append(page_num - 1)  # Convert to 0-indexed
            except ValueError:
                logger.warning("Invalid page number: %s", part)

    return sorted(set(page_indices))  # Remove duplicates and sort


def add_watermark(
    uploaded_file: UploadedFile,
    watermark_text: str = "CONFIDENTIAL",
    watermark_file: UploadedFile | None = None,
    position: str = "diagonal",
    x: float | None = None,
    y: float | None = None,
    color: str = "#000000",
    opacity: float = 0.3,
    font_size: int = 72,
    rotation: float = 0.0,
    scale: float = 1.0,
    pages: str = "all",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Add watermark to PDF.

    Args:
        uploaded_file: PDF file
        watermark_text: Text watermark
        watermark_file: Image file for watermark (optional)
        position: Position ('center' or 'diagonal')
        opacity: Opacity (0.1-1.0)
        font_size: Font size for text watermark
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "add_watermark",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "position": position,
        "opacity": opacity,
        "has_image": watermark_file is not None,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="watermark_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = "%s%s.pdf" % (base, suffix)
        output_path = os.path.join(tmp_dir, output_name)

        context.update({"pdf_path": pdf_path, "output_path": output_path})

        # Write uploaded file
        try:
            logger.debug(
                "Writing PDF file", extra={**context, "event": "file_write_start"}
            )
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except OSError as err:
            raise StorageError(
                "Failed to write PDF: %s" % err,
                context={**context, "error_type": type(err).__name__},
            ) from err

        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if (
                "password" in (validation_error or "").lower()
                or "encrypted" in (validation_error or "").lower()
            ):
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Repair PDF to handle potentially corrupted files
        pdf_path = repair_pdf(pdf_path)

        # Add watermark
        try:
            logger.info(
                "Adding watermark",
                extra={
                    **context,
                    "event": "watermark_start",
                    "watermark_text": watermark_text[:50] if watermark_text else None,
                    "has_image": watermark_file is not None,
                    "position": position,
                    "x": x,
                    "y": y,
                    "color": color,
                    "opacity": opacity,
                    "font_size": font_size,
                    "rotation": rotation,
                    "scale": scale,
                    "pages": pages,
                },
            )
            logger.debug(
                "Watermark parameters received: text='%s', file=%s, "
                "position='%s', x=%s, y=%s, color='%s', opacity=%s, "
                "font_size=%s, rotation=%s, scale=%s, pages='%s'",
                watermark_text,
                watermark_file is not None,
                position,
                x,
                y,
                color,
                opacity,
                font_size,
                rotation,
                scale,
                pages,
                extra=context,
            )

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            # Parse pages to watermark
            pages_to_watermark = parse_pages(pages, total_pages)
            context["pages_to_watermark"] = len(pages_to_watermark)

            for page_num in range(total_pages):
                page = reader.pages[page_num]

                # Skip if page is not in the list
                if page_num not in pages_to_watermark:
                    writer.add_page(page)
                    continue

                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                # Create watermark overlay
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.setFillAlpha(opacity)

                # Parse color (hex to RGB)
                try:
                    color_hex = color.lstrip("#")
                    color_r = int(color_hex[0:2], 16) / 255.0
                    color_g = int(color_hex[2:4], 16) / 255.0
                    color_b = int(color_hex[4:6], 16) / 255.0
                    can.setFillColorRGB(color_r, color_g, color_b)
                    logger.debug(
                        "Page %d: Applied color RGB(%.3f, %.3f, %.3f) from %s, opacity=%s",
                        page_num + 1,
                        color_r,
                        color_g,
                        color_b,
                        color,
                        opacity,
                        extra=context,
                    )
                except (ValueError, IndexError):
                    # Default to black if color parsing fails
                    can.setFillColorRGB(0, 0, 0)
                    logger.warning(
                        "Page %d: Failed to parse color '%s', using black",
                        page_num + 1,
                        color,
                        extra=context,
                    )

                if watermark_file:
                    # Image watermark
                    try:
                        # Reset file pointer to beginning
                        watermark_file.seek(0)
                        img = Image.open(watermark_file)

                        # Convert to RGB if necessary (for PNG with transparency, etc.)
                        if img.mode in ("RGBA", "LA", "P"):
                            # Create a white background for transparent images
                            background = Image.new("RGB", img.size, (255, 255, 255))
                            if img.mode == "P":
                                img = img.convert("RGBA")
                            background.paste(
                                img,
                                mask=(
                                    img.split()[-1]
                                    if img.mode in ("RGBA", "LA")
                                    else None
                                ),
                            )
                            img = background
                        elif img.mode != "RGB":
                            img = img.convert("RGB")

                        img_width, img_height = img.size
                        logger.debug(
                            "Image watermark loaded: %dx%d, mode: %s",
                            img_width,
                            img_height,
                            img.mode,
                            extra=context,
                        )

                        # Scale to fit page, then apply user scale
                        base_scale = (
                            min(page_width / img_width, page_height / img_height) * 0.5
                        )
                        scaled_width = img_width * base_scale * scale
                        scaled_height = img_height * base_scale * scale

                        # Calculate position
                        # For images, coordinates (x, y) represent the center point
                        # Priority: if coordinates are provided, use them regardless of position parameter
                        # IMPORTANT: JavaScript already converts coordinates from Canvas (top-left origin)
                        # to PDF system (bottom-left origin) before sending, so use them directly
                        if x is not None and y is not None:
                            # JavaScript sends coordinates already in PDF system (bottom-left origin)
                            # Use them directly without conversion
                            watermark_center_x = x
                            watermark_center_y = y
                            logger.debug(
                                "Page %d: Using provided coordinates (PDF: %.2f, %.2f) for image watermark",
                                page_num + 1,
                                watermark_center_x,
                                watermark_center_y,
                                extra=context,
                            )
                        elif position == "center":
                            watermark_center_x = page_width / 2
                            watermark_center_y = page_height / 2
                            logger.debug(
                                "Page %d: Using center position for image watermark",
                                page_num + 1,
                                extra=context,
                            )
                        else:  # diagonal (default) or custom without coordinates
                            # Place at center, rotation will be applied if needed
                            watermark_center_x = page_width / 2
                            watermark_center_y = page_height / 2
                            logger.debug(
                                "Page %d: Using default center position for image watermark",
                                page_num + 1,
                                extra=context,
                            )

                        # Calculate bottom-left corner for drawImage (ReportLab uses bottom-left origin)
                        watermark_x = watermark_center_x - scaled_width / 2
                        watermark_y = watermark_center_y - scaled_height / 2

                        # Save image to temp as PNG (ReportLab can handle PNG)
                        img_path = os.path.join(tmp_dir, "watermark_%d.png" % page_num)
                        # Save as RGB PNG (ReportLab works best with RGB)
                        img.save(img_path, "PNG")
                        logger.debug(
                            "Saved watermark image to %s", img_path, extra=context
                        )

                        # Apply rotation and scale transformations
                        # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                        should_apply_diagonal = (
                            position == "diagonal"
                            and rotation == 0
                            and (x is None or y is None)
                        )

                        if rotation != 0:
                            # Save state, apply rotation around center, draw, restore
                            can.saveState()
                            can.translate(watermark_center_x, watermark_center_y)
                            can.rotate(rotation)
                            can.translate(-watermark_center_x, -watermark_center_y)
                            can.drawImage(
                                img_path,
                                watermark_x,
                                watermark_y,
                                width=scaled_width,
                                height=scaled_height,
                                mask="auto",
                            )
                            can.restoreState()
                        elif should_apply_diagonal:
                            # Apply diagonal rotation only if no custom coordinates and rotation=0
                            can.saveState()
                            can.translate(watermark_center_x, watermark_center_y)
                            can.rotate(45)
                            can.translate(-watermark_center_x, -watermark_center_y)
                            can.drawImage(
                                img_path,
                                watermark_x,
                                watermark_y,
                                width=scaled_width,
                                height=scaled_height,
                                mask="auto",
                            )
                            can.restoreState()
                        else:
                            can.drawImage(
                                img_path,
                                watermark_x,
                                watermark_y,
                                width=scaled_width,
                                height=scaled_height,
                                mask="auto",
                            )
                    except Exception as img_err:
                        logger.warning(
                            "Failed to use image watermark: %s, using text",
                            img_err,
                            extra=context,
                        )
                        # Fallback to text - use same logic as text watermark below
                        _register_watermark_font()
                        scaled_font_size = font_size * scale
                        # Try to use Unicode font, fallback to Helvetica
                        try:
                            can.setFont("WatermarkFontBold", scaled_font_size)
                        except Exception:
                            can.setFont("Helvetica-Bold", scaled_font_size)

                        # Calculate text position (center point)
                        # IMPORTANT: JavaScript already converts coordinates from Canvas (top-left origin)
                        # to PDF system (bottom-left origin) before sending, so use them directly
                        if position == "custom" and x is not None and y is not None:
                            # JavaScript sends coordinates already in PDF system (bottom-left origin)
                            # Use them directly without conversion
                            watermark_x = x
                            watermark_y = y
                        else:
                            watermark_x = page_width / 2
                            watermark_y = page_height / 2

                        # Apply rotation and draw text
                        # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                        should_apply_diagonal = (
                            position == "diagonal"
                            and rotation == 0
                            and (x is None or y is None)
                        )

                        if rotation != 0:
                            can.saveState()
                            can.translate(watermark_x, watermark_y)
                            can.rotate(rotation)
                            can.translate(-watermark_x, -watermark_y)
                            can.drawCentredString(
                                watermark_x, watermark_y, watermark_text
                            )
                            can.restoreState()
                        elif should_apply_diagonal:
                            can.saveState()
                            can.translate(watermark_x, watermark_y)
                            can.rotate(45)
                            can.translate(-watermark_x, -watermark_y)
                            can.drawCentredString(
                                watermark_x, watermark_y, watermark_text
                            )
                            can.restoreState()
                        else:
                            can.drawCentredString(
                                watermark_x, watermark_y, watermark_text
                            )
                else:
                    # Text watermark
                    # Ensure watermark_text is not empty
                    if not watermark_text or not watermark_text.strip():
                        watermark_text = "CONFIDENTIAL"
                        logger.warning(
                            "Empty watermark_text, using default 'CONFIDENTIAL'",
                            extra=context,
                        )

                    # Register Unicode font if not already registered
                    _register_watermark_font()

                    # Apply scale to font size
                    scaled_font_size = font_size * scale
                    # Try to use Unicode font, fallback to Helvetica
                    try:
                        can.setFont("WatermarkFontBold", scaled_font_size)
                    except Exception:
                        can.setFont("Helvetica-Bold", scaled_font_size)

                    # Calculate text position
                    # For text, coordinates (x, y) represent the center point
                    # IMPORTANT: JavaScript already converts coordinates from Canvas (top-left origin)
                    # to PDF system (bottom-left origin) before sending, so use them directly
                    if x is not None and y is not None:
                        # JavaScript sends coordinates already in PDF system (bottom-left origin)
                        # Use them directly without conversion
                        watermark_x = x
                        watermark_y = y
                        logger.debug(
                            "Page %d: Using custom coordinates (PDF: %.2f, %.2f)",
                            page_num + 1,
                            watermark_x,
                            watermark_y,
                            extra=context,
                        )
                    elif position == "center":
                        watermark_x = page_width / 2
                        watermark_y = page_height / 2
                        logger.debug(
                            "Page %d: Using center position (%.2f, %.2f)",
                            page_num + 1,
                            watermark_x,
                            watermark_y,
                            extra=context,
                        )
                    else:  # diagonal (default) or custom without coordinates
                        # Place at center, rotation will be applied if needed
                        watermark_x = page_width / 2
                        watermark_y = page_height / 2
                        logger.debug(
                            "Page %d: Using default center position (%.2f, %.2f)",
                            page_num + 1,
                            watermark_x,
                            watermark_y,
                            extra=context,
                        )

                    # Apply rotation and scale, then draw text
                    # Text is drawn centered at (watermark_x, watermark_y)
                    # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                    should_apply_diagonal = (
                        position == "diagonal"
                        and rotation == 0
                        and (x is None or y is None)
                    )

                    logger.debug(
                        "Page %d text watermark: text='%s', "
                        "font_size=%s, position='%s', "
                        "x=%s, y=%s, watermark_pos=(%.2f, %.2f), "
                        "rotation=%s, scale=%s, should_apply_diagonal=%s, "
                        "color=%s, opacity=%s",
                        page_num + 1,
                        watermark_text,
                        scaled_font_size,
                        position,
                        x,
                        y,
                        watermark_x,
                        watermark_y,
                        rotation,
                        scale,
                        should_apply_diagonal,
                        color,
                        opacity,
                        extra=context,
                    )

                    if rotation != 0:
                        # Save state, apply rotation around text center, draw, restore
                        can.saveState()
                        can.translate(watermark_x, watermark_y)
                        can.rotate(rotation)
                        can.translate(-watermark_x, -watermark_y)
                        # Scale font size is already applied via scaled_font_size
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        can.restoreState()
                        logger.debug(
                            "Applied rotation %s degrees to text watermark",
                            rotation,
                            extra=context,
                        )
                    elif should_apply_diagonal:
                        # Only diagonal rotation if no custom coordinates and no custom rotation
                        can.saveState()
                        can.translate(watermark_x, watermark_y)
                        can.rotate(45)
                        can.translate(-watermark_x, -watermark_y)
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        can.restoreState()
                        logger.debug(
                            "Applied diagonal rotation (45 degrees) to text watermark",
                            extra=context,
                        )
                    else:
                        # Center position or custom with no rotation
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        logger.debug(
                            "Drew text watermark at (%.2f, %.2f) without rotation",
                            watermark_x,
                            watermark_y,
                            extra=context,
                        )

                can.save()

                # Merge watermark with page
                packet.seek(0)
                overlay = PdfReader(packet)
                overlay_page = overlay.pages[0]
                page.merge_page(overlay_page)
                writer.add_page(page)

            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.debug(
                "Watermark added", extra={**context, "event": "watermark_complete"}
            )

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to add watermark",
                extra={**error_context, "event": "watermark_error"},
                exc_info=True,
            )
            raise ConversionError(
                "Failed to add watermark: %s" % e, context=error_context
            ) from e

        # Validate output
        is_valid, validation_error = validate_output_file(
            output_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output PDF is invalid", context=context
            )

        output_size = os.path.getsize(output_path)
        logger.info(
            "Watermark added successfully",
            extra={
                **context,
                "event": "watermark_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return pdf_path, output_path

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
            "Unexpected error: %s" % e,
            context={**context, "error_type": type(e).__name__},
        ) from e
