# utils.py
import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
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
                logger.warning(f"Invalid page range: {part}")
        else:
            # Single page number
            try:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    page_indices.append(page_num - 1)  # Convert to 0-indexed
            except ValueError:
                logger.warning(f"Invalid page number: {part}")

    return sorted(set(page_indices))  # Remove duplicates and sort


logger = get_logger(__name__)


def crop_pdf(
    uploaded_file: UploadedFile,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    pages: str = "all",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Crop PDF pages.

    Args:
        uploaded_file: PDF file
        x: X coordinate (left edge)
        y: Y coordinate (bottom edge)
        width: Width of crop box (None = use remaining width)
        height: Height of crop box (None = use remaining height)
        pages: Pages to crop
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "crop_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "pages": pages,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="crop_pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}{suffix}.pdf"
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
                f"Failed to write PDF: {err}",
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

        # Crop PDF
        try:
            logger.info("Cropping PDF", extra={**context, "event": "crop_start"})

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            pages_to_crop = parse_pages(pages, total_pages)

            context["total_pages"] = total_pages
            context["pages_to_crop"] = len(pages_to_crop)

            # Get crop parameters for first page (assuming same crop for all pages)
            first_page = reader.pages[0]
            original_width = float(first_page.mediabox.width)
            original_height = float(first_page.mediabox.height)

            # Ensure x, y, width, height are valid numbers
            crop_x = float(x) if x is not None else 0.0
            crop_y = float(y) if y is not None else 0.0
            crop_width = (
                float(width)
                if width is not None and width > 0
                else (original_width - crop_x)
            )
            crop_height = (
                float(height)
                if height is not None and height > 0
                else (original_height - crop_y)
            )

            # Ensure crop box is within page bounds
            crop_x = max(0, min(crop_x, original_width))
            crop_y = max(0, min(crop_y, original_height))
            crop_width = max(
                10, min(crop_width, original_width - crop_x)
            )  # Minimum 10 points
            crop_height = max(
                10, min(crop_height, original_height - crop_y)
            )  # Minimum 10 points

            logger.info(
                ("Crop parameters: x=%.2f, y=%.2f, w=%.2f, " "h=%.2f, pages=%s"),
                crop_x,
                crop_y,
                crop_width,
                crop_height,
                pages_to_crop,
                extra=context,
            )

            # Convert PDF pages to images, crop them, and create new PDF
            # This is more reliable than just setting mediabox
            images = convert_from_path(pdf_path, dpi=150)

            # Create new PDF with cropped pages
            # Determine initial page size based on whether first page is cropped
            first_page_img = images[0] if images else None
            if first_page_img and 0 in pages_to_crop:
                initial_page_size = (crop_width, crop_height)
            elif first_page_img:
                dpi_ratio = 150 / 72
                initial_page_size = (
                    first_page_img.width / dpi_ratio * 72,
                    first_page_img.height / dpi_ratio * 72,
                )
            else:
                initial_page_size = (crop_width, crop_height)

            can = canvas.Canvas(output_path, pagesize=initial_page_size)
            dpi_ratio = 150 / 72

            for page_num in range(total_pages):
                if page_num >= len(images):
                    continue

                img = images[page_num]
                img_width_px = img.width
                img_height_px = img.height

                if page_num in pages_to_crop:
                    # Crop this page
                    # Convert crop coordinates from PDF points to image pixels
                    # PDF coordinates: crop_x is left, crop_y is bottom (from bottom-left origin)
                    # Image coordinates: (0,0) is top-left
                    crop_left_px = int(crop_x * dpi_ratio)
                    crop_bottom_px = int(crop_y * dpi_ratio)
                    crop_width_px = int(crop_width * dpi_ratio)
                    crop_height_px = int(crop_height * dpi_ratio)

                    # Convert PDF bottom-left origin to image top-left origin
                    crop_top_px = img_height_px - crop_bottom_px - crop_height_px

                    # Ensure crop area is within image bounds
                    crop_left_px = max(0, min(crop_left_px, img_width_px))
                    crop_top_px = max(0, min(crop_top_px, img_height_px))
                    crop_width_px = min(crop_width_px, img_width_px - crop_left_px)
                    crop_height_px = min(crop_height_px, img_height_px - crop_top_px)

                    if crop_width_px > 0 and crop_height_px > 0:
                        # Crop the image
                        cropped_img = img.crop(
                            (
                                crop_left_px,
                                crop_top_px,
                                crop_left_px + crop_width_px,
                                crop_top_px + crop_height_px,
                            )
                        )

                        # Set page size for cropped page
                        can.setPageSize((crop_width, crop_height))

                        # Save cropped image temporarily
                        img_path = os.path.join(tmp_dir, f"cropped_page_{page_num}.png")
                        cropped_img.save(img_path, "PNG")
                        can.drawImage(
                            img_path, 0, 0, width=crop_width, height=crop_height
                        )

                        logger.debug(
                            ("Cropping page %d: x=%.2f, y=%.2f, " "w=%.2f, h=%.2f"),
                            page_num + 1,
                            crop_x,
                            crop_y,
                            crop_width,
                            crop_height,
                            extra=context,
                        )
                else:
                    # Keep original page (no crop)
                    page_width = img_width_px / dpi_ratio * 72
                    page_height = img_height_px / dpi_ratio * 72
                    can.setPageSize((page_width, page_height))

                    # Save original image temporarily
                    img_path = os.path.join(tmp_dir, f"page_{page_num}.png")
                    img.save(img_path, "PNG")
                    can.drawImage(img_path, 0, 0, width=page_width, height=page_height)

                can.showPage()

            can.save()

            logger.debug("Crop completed", extra={**context, "event": "crop_complete"})

        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "Failed to crop PDF",
                extra={**error_context, "event": "crop_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to crop PDF: {e}", context=error_context
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
            "PDF cropped successfully",
            extra={
                **context,
                "event": "crop_success",
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
            f"Unexpected error: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
