"""
Asynchronous file utilities for better performance on 4GB servers.
Provides async file operations and batch processing.
"""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

# Thread pools for different file operations
FILE_IO_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="file_io")
PDF_PROCESSING_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdf_proc")


async def save_uploaded_file_async(
    uploaded_file: UploadedFile,
    file_path: str,
    chunk_size: int = 4 * 1024 * 1024,  # 4MB chunks
) -> None:
    """
    Asynchronously save uploaded file in chunks.

    Uses ThreadPoolExecutor to avoid blocking the main thread.
    """
    loop = asyncio.get_event_loop()

    await loop.run_in_executor(
        FILE_IO_POOL, _save_uploaded_file_sync, uploaded_file, file_path, chunk_size
    )


def _save_uploaded_file_sync(
    uploaded_file: UploadedFile, file_path: str, chunk_size: int
) -> None:
    """Synchronous file saving helper."""
    try:
        with open(file_path, "wb") as f:
            for chunk in uploaded_file.chunks(chunk_size=chunk_size):
                f.write(chunk)
    except OSError as e:
        logger.error(f"Failed to save file {file_path}: {e}")
        raise


async def batch_process_files_async(
    file_paths: list[str], processor_func, max_concurrent: int = 2
) -> list[tuple[str, any]]:
    """
    Process multiple files concurrently with limited concurrency.

    Args:
        file_paths: List of file paths to process
        processor_func: Function to process each file
        max_concurrent: Maximum concurrent processes

    Returns:
        List of (file_path, result) tuples
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(file_path: str):
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                PDF_PROCESSING_POOL, processor_func, file_path
            )

    tasks = [process_with_semaphore(path) for path in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return list(zip(file_paths, results, strict=False))


async def get_file_size_async(file_path: str) -> int:
    """Get file size asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(FILE_IO_POOL, os.path.getsize, file_path)


async def cleanup_temp_files_async(temp_dir: str, max_age_seconds: int = 3600) -> int:
    """
    Asynchronously clean up temporary files older than max_age_seconds.

    Returns:
        Number of files cleaned up
    """
    import time

    loop = asyncio.get_event_loop()

    def cleanup_sync():
        cleaned_count = 0
        current_time = time.time()

        if not os.path.exists(temp_dir):
            return cleaned_count

        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(item_path):
                    file_age = current_time - os.path.getmtime(item_path)
                    if file_age > max_age_seconds:
                        os.remove(item_path)
                        cleaned_count += 1
                elif os.path.isdir(item_path):
                    # For directories, check the oldest file inside
                    dir_age = current_time - os.path.getmtime(item_path)
                    if dir_age > max_age_seconds:
                        import shutil

                        shutil.rmtree(item_path, ignore_errors=True)
                        cleaned_count += 1
            except OSError as e:
                logger.warning(f"Failed to cleanup {item_path}: {e}")

        return cleaned_count

    return await loop.run_in_executor(FILE_IO_POOL, cleanup_sync)


class AsyncFileManager:
    """
    Context manager for async file operations with automatic cleanup.
    """

    def __init__(self, prefix: str = "convertica_async"):
        self.prefix = prefix
        self.temp_dir = None
        self.managed_files = []

    async def __aenter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix=self.prefix)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()

    async def save_file(self, uploaded_file: UploadedFile, filename: str) -> str:
        """Save uploaded file and track for cleanup."""
        file_path = os.path.join(self.temp_dir, filename)
        await save_uploaded_file_async(uploaded_file, file_path)
        self.managed_files.append(file_path)
        return file_path

    async def cleanup_all(self):
        """Clean up all managed files and temp directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            await cleanup_temp_files_async(self.temp_dir, 0)  # Clean all files
            try:
                import shutil

                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except OSError as e:
                logger.warning(f"Failed to cleanup temp dir {self.temp_dir}: {e}")
