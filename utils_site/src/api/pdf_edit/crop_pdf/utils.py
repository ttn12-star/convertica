import os

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor
from ...pdf_utils import parse_pages

logger = get_logger(__name__)


def crop_pdf(
    uploaded_file: UploadedFile,
    x: float = 0.0,
    y: float = 0.0,
    width: float = None,
    height: float = None,
    pages: str = "all",
    scale_to_page_size: bool = False,
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
        scale_to_page_size: Scale cropped area to full page size
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "crop_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "pages": pages,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="crop_pdf_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()

        tmp_dir = processor.tmp_dir or ""

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = f"{base}{suffix}.pdf"
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        # Crop PDF
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            pages_to_crop = set(parse_pages(pages, total_pages))

            context["total_pages"] = total_pages
            context["pages_to_crop"] = len(pages_to_crop)

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

            if not scale_to_page_size:
                # Fast path: modify cropbox/mediabox without rasterization
                writer = PdfWriter()
                for page_num in range(total_pages):
                    page = reader.pages[page_num]
                    if page_num in pages_to_crop:
                        page.cropbox.lower_left = (crop_x, crop_y)
                        page.cropbox.upper_right = (
                            crop_x + crop_width,
                            crop_y + crop_height,
                        )
                        page.mediabox.lower_left = (crop_x, crop_y)
                        page.mediabox.upper_right = (
                            crop_x + crop_width,
                            crop_y + crop_height,
                        )
                    writer.add_page(page)

                with open(output_path, "wb") as output_file:
                    writer.write(output_file)

                processor.validate_output_pdf(output_path, min_size=1000)
                return pdf_path, output_path

            # Slow path: keep old behavior (scale_to_page_size=True) with rasterization
            from pdf2image import convert_from_path

            if not tmp_dir:
                tmp_dir = os.path.dirname(output_path)

            # Create new PDF with cropped pages
            # Determine initial page size based on whether first page is cropped
            images = convert_from_path(pdf_path, dpi=150)
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
                        if scale_to_page_size:
                            # Scale cropped area to full page size
                            page_size = (original_width, original_height)
                        else:
                            # Use cropped area size
                            page_size = (crop_width, crop_height)

                        can.setPageSize(page_size)

                        # Save cropped image temporarily
                        img_path = os.path.join(tmp_dir, f"cropped_page_{page_num}.png")
                        cropped_img.save(img_path, "PNG")

                        if scale_to_page_size:
                            # Draw cropped image scaled to full page size
                            can.drawImage(
                                img_path,
                                0,
                                0,
                                width=original_width,
                                height=original_height,
                            )
                        else:
                            # Draw cropped image at actual size
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

        processor.validate_output_pdf(output_path, min_size=1000)
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
