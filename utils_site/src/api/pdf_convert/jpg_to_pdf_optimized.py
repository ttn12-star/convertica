"""
Optimized JPG to PDF conversion with parallel processing.
"""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from utils_site.src.api.file_validation import check_disk_space, sanitize_filename
from utils_site.src.api.logging_utils import get_logger
from utils_site.src.api.parallel_processing import (
    get_optimal_batch_size,
    process_images_parallel,
)
from utils_site.src.exceptions import ConversionError, InvalidPDFError

logger = get_logger(__name__)


class OptimizedJPGToPDFConverter:
    """
    Optimized JPG to PDF converter with parallel image processing.
    """

    def __init__(self):
        self.max_image_size = 2000  # Max dimension for memory efficiency
        self.default_quality = 85

    def optimize_image(self, image_path: str, output_dir: str) -> str | None:
        """
        Optimize a single image for PDF conversion.

        Args:
            image_path: Path to input image
            output_dir: Directory for optimized image

        Returns:
            Path to optimized image or None if failed
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Resize if too large for memory efficiency
                if img.width > self.max_image_size or img.height > self.max_image_size:
                    img.thumbnail(
                        (self.max_image_size, self.max_image_size),
                        Image.Resampling.LANCZOS,
                    )

                # Save optimized image
                basename = os.path.basename(image_path)
                name, ext = os.path.splitext(basename)
                optimized_path = os.path.join(output_dir, f"{name}_opt.jpg")

                img.save(
                    optimized_path, "JPEG", quality=self.default_quality, optimize=True
                )
                return optimized_path

        except Exception as e:
            logger.error(f"Failed to optimize image {image_path}: {e}")
            return None

    async def convert_multiple_images_to_pdf(
        self,
        image_paths: list[str],
        output_path: str,
        page_size: str = "letter",
        margin: int = 72,  # 1 inch margin
        context: dict = None,
    ) -> str:
        """
        Convert multiple images to PDF with parallel processing.

        Args:
            image_paths: List of image file paths
            output_path: Output PDF path
            page_size: Page size ("letter" or "a4")
            margin: Page margin in points
            context: Logging context

        Returns:
            Path to output PDF
        """
        if context is None:
            context = {}

        # Get page dimensions
        if page_size.lower() == "a4":
            page_width, page_height = A4
        else:
            page_width, page_height = letter

        # Calculate available area for images
        available_width = page_width - (2 * margin)
        available_height = page_height - (2 * margin)

        logger.info(
            f"Converting {len(image_paths)} images to PDF with parallel processing",
            extra={**context, "total_images": len(image_paths), "page_size": page_size},
        )

        # Create temporary directory for optimized images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Optimize images in parallel
            optimized_paths = await process_images_parallel(
                image_paths=image_paths,
                output_dir=temp_dir,
                quality=self.default_quality,
                batch_size=get_optimal_batch_size(
                    len(image_paths) * 2
                ),  # Estimate batch size
                context={**context, "stage": "optimization"},
            )

            if not optimized_paths:
                raise ConversionError("No images could be optimized", context=context)

            # Create PDF with optimized images
            c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

            for i, optimized_path in enumerate(optimized_paths):
                try:
                    # Add image to PDF page
                    self._add_image_to_canvas(
                        c, optimized_path, available_width, available_height, margin
                    )

                    # Add new page for next image (except last one)
                    if i < len(optimized_paths) - 1:
                        c.showPage()

                except Exception as e:
                    logger.error(
                        f"Failed to add image {optimized_path} to PDF: {e}",
                        extra={
                            **context,
                            "image_index": i,
                            "image_path": optimized_path,
                        },
                    )
                    continue

            c.save()

        # Verify PDF was created
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ConversionError("PDF creation failed", context=context)

        logger.info(
            f"JPG to PDF conversion completed: {len(optimized_paths)} images",
            extra={
                **context,
                "event": "conversion_complete",
                "successful_images": len(optimized_paths),
            },
        )

        return output_path

    def _add_image_to_canvas(
        self,
        canvas_obj: canvas.Canvas,
        image_path: str,
        max_width: float,
        max_height: float,
        margin: float,
    ):
        """
        Add an image to PDF canvas with proper scaling and centering.

        Args:
            canvas_obj: ReportLab canvas object
            image_path: Path to image file
            max_width: Maximum width available
            max_height: Maximum height available
            margin: Page margin
        """
        try:
            # Get image dimensions
            with Image.open(image_path) as img:
                img_width, img_height = img.size

            # Calculate scaling to fit within available area
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale = min(width_ratio, height_ratio)

            # Calculate scaled dimensions
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            # Center the image on the page
            x = margin + (max_width - scaled_width) / 2
            y = margin + (max_height - scaled_height) / 2

            # Draw image on canvas
            canvas_obj.drawImage(
                ImageReader(image_path),
                x,
                y,
                scaled_width,
                scaled_height,
                preserveAspectRatio=True,
                mask="auto",
            )

        except Exception as e:
            logger.error(f"Failed to add image to canvas: {e}")
            raise


async def convert_jpg_to_pdf_optimized(
    uploaded_file: UploadedFile,
    page_size: str = "letter",
    margin: int = 72,
    quality: int = 85,
    suffix: str = "_convertica",
    context: dict = None,
) -> tuple[str, str]:
    """
    Optimized JPG to PDF conversion with parallel processing.

    Args:
        uploaded_file: Uploaded file object (can be single image or ZIP)
        page_size: Page size ("letter" or "a4")
        margin: Page margin in points
        quality: JPEG quality for optimization
        suffix: Suffix for output filename
        context: Logging context

    Returns:
        Tuple of (input_path, output_path)
    """
    if context is None:
        context = {}

    # Create converter with specified quality
    converter = OptimizedJPGToPDFConverter()
    converter.default_quality = quality

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded file
        input_filename = sanitize_filename(uploaded_file.name)
        base_name = os.path.splitext(input_filename)[0]
        input_path = os.path.join(temp_dir, input_filename)

        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Check if it's a ZIP file with multiple images
        if input_filename.lower().endswith(".zip"):
            import zipfile

            image_paths = []

            with zipfile.ZipFile(input_path, "r") as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith(
                        (".jpg", ".jpeg", ".png", ".bmp", ".gif")
                    ):
                        # Extract image
                        extracted_path = os.path.join(
                            temp_dir, os.path.basename(file_info.filename)
                        )
                        with zip_ref.open(file_info) as source, open(
                            extracted_path, "wb"
                        ) as target:
                            target.write(source.read())
                        image_paths.append(extracted_path)
        else:
            # Single image file
            image_paths = [input_path]

        if not image_paths:
            raise ConversionError("No valid images found", context=context)

        # Generate output path
        output_filename = f"{base_name}{suffix}.pdf"
        output_path = os.path.join(temp_dir, output_filename)

        # Convert images to PDF
        result_path = await converter.convert_multiple_images_to_pdf(
            image_paths=image_paths,
            output_path=output_path,
            page_size=page_size,
            margin=margin,
            context={**context, "conversion_type": "jpg_to_pdf_optimized"},
        )

        return input_path, result_path
