"""
Maintenance tasks for Convertica.

These tasks handle periodic maintenance operations like
cleaning up temporary files, updating statistics, etc.
"""

import os
import shutil
import time
from pathlib import Path

from celery import shared_task
from django.conf import settings
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

# Default async temp directory - uses MEDIA_ROOT for shared access
ASYNC_TEMP_DIR = getattr(
    settings,
    "ASYNC_TEMP_DIR",
    Path(getattr(settings, "MEDIA_ROOT", "/app/media")) / "async_temp",
)


@shared_task(name="maintenance.cleanup_temp_files", queue="maintenance")
def cleanup_temp_files():
    """
    Clean up temporary files older than 1 hour.

    This task should be run periodically (e.g., every hour)
    to remove old temporary files from the filesystem.
    """
    try:
        temp_dir = Path(settings.BASE_DIR) / "tmp"
        if not temp_dir.exists():
            return {"status": "success", "cleaned": 0}

        current_time = time.time()
        cleaned_count = 0
        total_size = 0

        # Clean files older than 1 hour
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 3600:  # 1 hour
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_count += 1
                        total_size += file_size
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")

        logger.info(
            f"Cleanup completed: {cleaned_count} files, "
            f"{total_size / (1024 * 1024):.2f} MB freed"
        )

        return {
            "status": "success",
            "cleaned": cleaned_count,
            "size_freed_mb": round(total_size / (1024 * 1024), 2),
        }

    except Exception as exc:
        logger.error(f"Cleanup failed: {str(exc)}", exc_info=True)
        return {"status": "error", "message": str(exc)}


@shared_task(name="maintenance.cleanup_async_temp_files", queue="maintenance")
def cleanup_async_temp_files(max_age_seconds: int = 3600):
    """
    Clean up temporary files from async conversion tasks.

    This task removes task directories older than max_age_seconds.
    Should be run periodically (e.g., every 30 minutes).

    Args:
        max_age_seconds: Maximum age of files in seconds (default: 1 hour)
    """
    try:
        async_dir = Path(ASYNC_TEMP_DIR)
        if not async_dir.exists():
            return {"status": "success", "cleaned": 0, "size_freed_mb": 0}

        current_time = time.time()
        cleaned_count = 0
        total_size = 0

        # Iterate through task directories
        for task_dir in async_dir.iterdir():
            if not task_dir.is_dir():
                continue

            try:
                # Check directory age by looking at modification time
                dir_age = current_time - task_dir.stat().st_mtime
                if dir_age > max_age_seconds:
                    # Calculate size before deletion
                    dir_size = sum(
                        f.stat().st_size for f in task_dir.rglob("*") if f.is_file()
                    )

                    # Remove the entire task directory
                    shutil.rmtree(task_dir, ignore_errors=True)
                    cleaned_count += 1
                    total_size += dir_size
                    logger.debug(f"Cleaned up task directory: {task_dir.name}")

            except Exception as e:
                logger.warning(f"Failed to clean task dir {task_dir}: {e}")

        size_freed_mb = round(total_size / (1024 * 1024), 2)
        logger.info(
            f"Async cleanup completed: {cleaned_count} task dirs, "
            f"{size_freed_mb} MB freed"
        )

        return {
            "status": "success",
            "cleaned": cleaned_count,
            "size_freed_mb": size_freed_mb,
        }

    except Exception as exc:
        logger.error(f"Async cleanup failed: {str(exc)}", exc_info=True)
        return {"status": "error", "message": str(exc)}


@shared_task(name="maintenance.update_statistics", queue="maintenance")
def update_statistics():
    """
    Update site statistics (conversion counts, popular tools, etc.).

    This task can be used to aggregate and cache statistics
    for dashboard or analytics purposes.
    """
    try:
        # Placeholder for statistics update logic
        # This can be expanded to track conversion metrics,
        # popular tools, user activity, etc.

        logger.info("Statistics update completed")

        return {"status": "success"}

    except Exception as exc:
        logger.error(f"Statistics update failed: {str(exc)}", exc_info=True)
        return {"status": "error", "message": str(exc)}
