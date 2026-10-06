import os

from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader, PdfWriter
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

            # Scale the crop up to the original page size, vector to vector:
            # this path used to rasterize EVERY page at 150 DPI (text became
            # a picture, untouched pages included) and stretch the crop to the
            # page without keeping its proportions.
            import fitz

            with fitz.open(pdf_path) as src, fitz.open() as out:
                for page_num, page in enumerate(src):
                    if page_num not in pages_to_crop:
                        out.insert_pdf(src, from_page=page_num, to_page=page_num)
                        continue
                    # crop_* are PDF units from the bottom-left of the page;
                    # PyMuPDF measures from the top-left of the unrotated page.
                    height = page.cropbox.height
                    clip = (
                        fitz.Rect(
                            crop_x,
                            height - crop_y - crop_height,
                            crop_x + crop_width,
                            height - crop_y,
                        )
                        * page.rotation_matrix
                    )
                    target = out.new_page(width=original_width, height=original_height)
                    target.show_pdf_page(
                        target.rect, src, page_num, clip=clip, keep_proportion=True
                    )
                out.save(output_path, garbage=3, deflate=True)

        except InvalidPDFError:
            raise  # user-facing 400 (e.g. page range "5-2"), not a 500
        except Exception as e:
            from pypdf.errors import PyPdfError

            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            # A pypdf parse error means the upload is corrupt/truncated — that's
            # bad input (400), not a server fault. Log it at warning and surface
            # it as InvalidPDFError so both single and batch paths return 4xx
            # instead of a Sentry-alerting 500.
            if isinstance(e, PyPdfError):
                logger.warning(
                    "Failed to crop PDF: invalid input",
                    extra={**error_context, "event": "crop_error"},
                )
                raise InvalidPDFError(
                    f"Failed to crop PDF: {e}", context=error_context
                ) from e
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
