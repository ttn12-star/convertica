"""
Maintenance tasks for Convertica.

These tasks handle periodic maintenance operations like
cleaning up temporary files, updating statistics, etc.
"""

import os
import time
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from src.api.logging_utils import get_logger

logger = get_logger(__name__)


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
