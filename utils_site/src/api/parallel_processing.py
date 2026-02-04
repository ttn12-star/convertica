"""
Parallel processing utilities for adaptive server optimization.
Provides memory-safe batch processing for large files based on available resources.
"""

import atexit
import os
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf2image import convert_from_path
from PIL import Image

from .logging_utils import get_logger
from .performance_config import get_performance_config

logger = get_logger(__name__)

# Get adaptive configuration
perf_config = get_performance_config()

# Thread pools optimized for current server resources
BATCH_PROCESSING_POOL = ThreadPoolExecutor(
    max_workers=perf_config.get_thread_workers("batch_processing"),
    thread_name_prefix="batch_proc",
)
IMAGE_PROCESSING_POOL = ThreadPoolExecutor(
    max_workers=perf_config.get_thread_workers("image_processing"),
    thread_name_prefix="img_proc",
)


def _cleanup_thread_pools():
    """Cleanup thread pools on interpreter shutdown to prevent resource leaks."""
    try:
        BATCH_PROCESSING_POOL.shutdown(wait=False)
        IMAGE_PROCESSING_POOL.shutdown(wait=False)
        logger.debug("Thread pools cleaned up successfully")
    except Exception as e:
        logger.warning(f"Error during thread pool cleanup: {e}")


# Register cleanup function to run on interpreter exit
atexit.register(_cleanup_thread_pools)


class MemorySafeBatchProcessor:
    """
    Memory-safe batch processor for large files.
    Processes items in small batches to prevent memory overflow.
    """

    def __init__(self, batch_size: int = None, max_memory_mb: int = None):
        # Use adaptive configuration if not specified
        if batch_size is None:
            batch_size = perf_config.get_batch_size("pdf_pages")
        if max_memory_mb is None:
            max_memory_mb = perf_config.get_memory_limit("max_batch_memory_mb")

        self.batch_size = batch_size
        self.max_memory_mb = max_memory_mb

    def process_batch(
        self, items: list[any], processor_func: Callable, context: dict = None
    ) -> list[any]:
        """
        Process items in memory-safe batches.

        Args:
            items: List of items to process
            processor_func: Function to process each item
            context: Logging context

        Returns:
            List of processed results
        """
        if context is None:
            context = {}

        results = []
        total_items = len(items)

        logger.info(
            f"Starting batch processing: {total_items} items, batch_size={self.batch_size}",
            extra={
                **context,
                "event": "batch_processing_start",
                "total_items": total_items,
            },
        )

        for i in range(0, total_items, self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1

            logger.debug(
                f"Processing batch {batch_num}/{(total_items + self.batch_size - 1) // self.batch_size}",
                extra={**context, "batch_num": batch_num, "batch_size": len(batch)},
            )

            try:
                # Process batch with thread pool
                batch_results = []
                with ThreadPoolExecutor(
                    max_workers=perf_config.get_thread_workers("batch_processing")
                ) as executor:
                    future_to_item = {
                        executor.submit(processor_func, item): item for item in batch
                    }

                    for future in as_completed(future_to_item):
                        try:
                            result = future.result(timeout=30)  # 30s timeout per item
                            batch_results.append(result)
                        except Exception as e:
                            logger.error(
                                f"Failed to process item in batch {batch_num}",
                                extra={
                                    **context,
                                    "batch_num": batch_num,
                                    "error": str(e),
                                },
                                exc_info=True,
                            )
                            # Continue with other items in batch
                            continue

                results.extend(batch_results)

                # Force garbage collection for memory
                del batch_results
                import gc

                gc.collect()

            except Exception as e:
                logger.error(
                    f"Batch {batch_num} failed completely",
                    extra={**context, "batch_num": batch_num, "error": str(e)},
                    exc_info=True,
                )
                continue

        logger.info(
            f"Batch processing completed: {len(results)}/{total_items} items successful",
            extra={
                **context,
                "event": "batch_processing_complete",
                "successful": len(results),
            },
        )

        return results

    def process_in_batches(
        self, items: list[any], processor_func: Callable, context: dict = None
    ) -> list[any]:
        return self.process_batch(items, processor_func, context)


async def process_pdf_pages_parallel(
    pdf_path: str,
    dpi: int = 150,
    batch_size: int = 5,
    pages: list[int] | None = None,
    context: dict = None,
) -> list[Image.Image]:
    """
    Process PDF pages in parallel batches for memory efficiency.

    Args:
        pdf_path: Path to PDF file
        dpi: DPI for image conversion
        batch_size: Number of pages to process at once
        pages: Specific pages to process (None for all)
        context: Logging context

    Returns:
        List of PIL Image objects
    """
    if context is None:
        context = {}

    try:
        # Get total page count first
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        with open(pdf_path, "rb") as f:
            pdf_reader = PdfReader(f)
            total_pages = len(pdf_reader.pages)

        # Determine which pages to process
        if pages is not None:
            pages_to_process = [p for p in pages if p < total_pages]
        else:
            pages_to_process = list(range(total_pages))

        logger.info(
            f"Processing {len(pages_to_process)} PDF pages in batches of {batch_size}",
            extra={
                **context,
                "total_pages": total_pages,
                "pages_to_process": len(pages_to_process),
            },
        )

        # Process in batches
        processor = MemorySafeBatchProcessor(batch_size=batch_size)

        def process_page_batch(page_batch: list[int]) -> list[Image.Image]:
            """Process a batch of pages."""
            try:
                # Convert only the pages in this batch
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=page_batch[0] + 1,  # pdf2image uses 1-based indexing
                    last_page=page_batch[-1] + 2,
                    fmt="jpeg",
                )

                # Filter to only the pages we want
                result_images = []
                for i, page_num in enumerate(page_batch):
                    if i < len(images):
                        result_images.append(images[i])

                return result_images

            except Exception as e:
                logger.error(
                    f"Failed to process page batch {page_batch}",
                    extra={**context, "page_batch": page_batch, "error": str(e)},
                    exc_info=True,
                )
                return []

        # Create page batches
        page_batches = []
        for i in range(0, len(pages_to_process), batch_size):
            page_batches.append(pages_to_process[i : i + batch_size])

        # Process batches
        all_images = []
        for batch_result in processor.process_in_batches(
            page_batches, process_page_batch, context
        ):
            all_images.extend(batch_result)

        logger.info(
            f"PDF processing completed: {len(all_images)} pages processed",
            extra={
                **context,
                "event": "pdf_processing_complete",
                "processed_pages": len(all_images),
            },
        )

        return all_images

    except Exception as e:
        logger.error(
            "PDF parallel processing failed",
            extra={**context, "error": str(e)},
            exc_info=True,
        )
        raise


async def process_images_parallel(
    image_paths: list[str],
    output_dir: str,
    quality: int = 85,
    batch_size: int = 10,
    context: dict = None,
) -> list[str]:
    """
    Process multiple images in parallel for JPG-to-PDF conversion.

    Args:
        image_paths: List of image file paths
        output_dir: Directory for processed images
        quality: JPEG quality (1-100)
        batch_size: Number of images to process at once
        context: Logging context

    Returns:
        List of processed image paths
    """
    if context is None:
        context = {}

    def process_single_image(image_path: str) -> str | None:
        """Process a single image."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Optimize for PDF
                # Only resize if quality is low AND image is extremely large
                max_size = 4000  # Increased from 2000 for better quality
                should_resize = quality < 85 and (
                    img.width > max_size or img.height > max_size
                )

                if should_resize:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Save processed image
                basename = os.path.basename(image_path)
                name, ext = os.path.splitext(basename)
                processed_path = os.path.join(output_dir, f"{name}_processed.jpg")

                # For high quality, use better settings
                if quality >= 90:
                    img.save(
                        processed_path,
                        "JPEG",
                        quality=quality,
                        subsampling=0,
                        optimize=False,
                    )
                else:
                    img.save(processed_path, "JPEG", quality=quality, optimize=True)
                return processed_path

        except Exception as e:
            logger.error(
                f"Failed to process image {image_path}",
                extra={**context, "image_path": image_path, "error": str(e)},
                exc_info=True,
            )
            return None

    logger.info(
        f"Processing {len(image_paths)} images in batches of {batch_size}",
        extra={**context, "total_images": len(image_paths)},
    )

    # Process in batches
    processor = MemorySafeBatchProcessor(batch_size=batch_size)
    processed_paths = processor.process_in_batches(
        image_paths, process_single_image, context
    )

    # Filter out None results
    successful_paths = [path for path in processed_paths if path is not None]

    logger.info(
        f"Image processing completed: {len(successful_paths)}/{len(image_paths)} successful",
        extra={
            **context,
            "event": "image_processing_complete",
            "successful": len(successful_paths),
        },
    )

    return successful_paths


def get_optimal_batch_size(
    file_size_mb: float,
    operation_type: str = "pdf_pages",
    memory_gb: float | None = None,
) -> int:
    """
    Calculate optimal batch size based on file size and available memory.

    Args:
        file_size_mb: File size in MB
        operation_type: Type of operation
        memory_gb: Available memory in GB

    Returns:
        Optimal batch size (1-10)
    """
    # Base batch sizes for different file sizes
    # If caller didn't pass memory, use detected server memory
    if memory_gb is None:
        try:
            memory_gb = perf_config.total_memory_gb
        except Exception:
            memory_gb = 4.0

    # Base batch sizes for different file sizes
    if file_size_mb < 10:
        base = 10
    elif file_size_mb < 50:
        base = 5
    elif file_size_mb < 100:
        base = 3
    else:
        base = 2

    # On low-memory servers, be more conservative
    if memory_gb < 4:
        return max(1, min(base, 2))
    return base


async def optimize_pdf_to_jpg_conversion(
    pdf_path: str,
    output_zip_path: str,
    dpi: int = 150,
    pages: list[int] | None = None,
    context: dict = None,
) -> str:
    """
    Optimized PDF-to-JPG conversion using parallel processing.

    Args:
        pdf_path: Input PDF path
        output_zip_path: Output ZIP path
        dpi: DPI for conversion
        pages: Specific pages to convert
        context: Logging context

    Returns:
        Path to output ZIP file
    """
    if context is None:
        context = {}

    # Get file size for optimal batch size
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    batch_size = get_optimal_batch_size(file_size_mb, operation_type="pdf_pages")

    logger.info(
        f"Starting optimized PDF-to-JPG conversion: file_size={file_size_mb:.1f}MB, batch_size={batch_size}",
        extra={**context, "file_size_mb": file_size_mb, "batch_size": batch_size},
    )

    # Process PDF pages in parallel
    images = await process_pdf_pages_parallel(
        pdf_path=pdf_path,
        dpi=dpi,
        batch_size=batch_size,
        pages=pages,
        context={**context, "conversion_type": "pdf_to_jpg"},
    )

    # Create ZIP file
    import zipfile

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        for idx, image in enumerate(images):
            page_num = idx + 1
            if pages is not None:
                page_num = pages[idx] + 1

            jpg_name = f"{base_name}_page{page_num:04d}.jpg"

            # Save image to temporary file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                image.save(tmp.name, "JPEG", quality=90, optimize=True)
                zipf.write(tmp.name, jpg_name)
                os.unlink(tmp.name)

    logger.info(
        f"PDF-to-JPG conversion completed: {len(images)} pages in {os.path.getsize(output_zip_path)/(1024*1024):.1f}MB ZIP",
        extra={
            **context,
            "event": "pdf_to_jpg_complete",
            "pages_converted": len(images),
        },
    )

    return output_zip_path
