import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from src.exceptions import ConversionError, InvalidPDFError, StorageError

from ...file_validation import check_disk_space, sanitize_filename, validate_output_file
from ...logging_utils import get_logger
from ...optimization_manager import optimization_manager
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


async def convert_jpg_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica", **kwargs
) -> tuple[str, str]:
    """
    Convert JPG to PDF using adaptive optimization.

    Args:
        uploaded_file: Uploaded JPG file
        suffix: Suffix for output filename
        **kwargs: Additional parameters (e.g., quality)
    """
    return await optimization_manager.convert_jpg_to_pdf(
        uploaded_file, suffix=suffix, **kwargs
    )


async def convert_multiple_jpg_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """
    Convert multiple JPGs to PDF using adaptive optimization.

    Args:
        uploaded_file: Uploaded ZIP file with JPGs
        suffix: Suffix for output filename
    """
    return await optimization_manager.convert_jpg_to_pdf(uploaded_file, suffix=suffix)


async def _convert_jpg_to_pdf_sequential(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
    tmp_dir: str = None,
    context: dict = None,
    quality: int = 85,
    **kwargs,
) -> tuple[str, str]:
    """Sequential JPG to PDF conversion (fallback implementation)."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="jpg2pdf_")

    if context is None:
        context = {}

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))

    image_path = os.path.join(tmp_dir, safe_name)
    base = os.path.splitext(safe_name)[0]
    pdf_name = f"{base}{suffix}.pdf"
    pdf_path = os.path.join(tmp_dir, pdf_name)

    # Save uploaded file
    with open(image_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Process image with quality control
    processed_path = image_path
    with Image.open(image_path) as image:
        needs_conversion = image.mode in ("RGBA", "LA", "P")

        # For high quality (>= 90) and RGB images, use original
        if quality >= 90 and not needs_conversion:
            processed_path = image_path
        else:
            # Convert/optimize image with specified quality
            if needs_conversion:
                image = image.convert("RGB")

            processed_path = os.path.join(tmp_dir, f"processed_{safe_name}")
            if quality >= 90:
                image.save(
                    processed_path,
                    "JPEG",
                    quality=quality,
                    subsampling=0,
                    optimize=False,
                )
            else:
                image.save(processed_path, "JPEG", quality=quality, optimize=True)

        # Get image dimensions
        img_width, img_height = image.size

        # Create PDF with A4 page size
        c = canvas.Canvas(pdf_path, pagesize=A4)
        page_width, page_height = A4

        # Calculate scaling to fit image on page
        margin = 72  # 1 inch margin
        available_width = page_width - (2 * margin)
        available_height = page_height - (2 * margin)

        width_ratio = available_width / img_width
        height_ratio = available_height / img_height
        scale = min(width_ratio, height_ratio)

        scaled_width = img_width * scale
        scaled_height = img_height * scale

        # Center image on page
        x = margin + (available_width - scaled_width) / 2
        y = margin + (available_height - scaled_height) / 2

        # Draw image
        c.drawImage(ImageReader(processed_path), x, y, scaled_width, scaled_height)
        c.save()

    return image_path, pdf_path
