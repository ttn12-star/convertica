"""
Parallel processing utilities for adaptive server optimization.
Provides memory-safe batch processing for large files based on available resources.
"""

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

from .logging_utils import get_logger
from .performance_config import get_performance_config

logger = get_logger(__name__)

# Get adaptive configuration
perf_config = get_performance_config()


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
