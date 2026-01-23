"""
Maintenance tasks for Convertica.

These tasks handle periodic maintenance operations like
cleaning up temporary files, updating statistics, etc.
"""

import gc
import shutil
import time
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

# Default async temp directory - uses MEDIA_ROOT for shared access
_media_root = getattr(settings, "MEDIA_ROOT", None)
if _media_root is None:
    _media_root = Path("/app/media")
else:
    _media_root = Path(_media_root)  # Convert string to Path if needed

ASYNC_TEMP_DIR = getattr(
    settings,
    "ASYNC_TEMP_DIR",
    _media_root / "async_temp",
)


@shared_task(name="maintenance.memory_cleanup", queue="maintenance")
def memory_cleanup():
    """
    Memory cleanup task for 4GB servers.

    This task runs every 15 minutes to:
    - Force garbage collection
    - Clear Python memory caches
    - Log memory usage for monitoring
    """
    try:
        # Force garbage collection
        collected = gc.collect()

        # Get memory stats if psutil is available
        memory_info = {}
        try:
            import psutil

            process = psutil.Process()
            memory_info = {
                "rss_mb": process.memory_info().rss / 1024 / 1024,
                "vms_mb": process.memory_info().vms / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
            }
        except ImportError:
            # psutil not available, just log basic info
            pass

        logger.info(
            f"Memory cleanup completed - collected {collected} objects",
            extra={
                "event": "memory_cleanup",
                "objects_collected": collected,
                **memory_info,
            },
        )

        return {
            "status": "success",
            "objects_collected": collected,
            "memory_info": memory_info,
        }

    except Exception as e:
        logger.error(
            f"Memory cleanup failed: {e}",
            extra={"event": "memory_cleanup_failed", "error": str(e)},
        )
        return {"status": "failed", "error": str(e)}


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


@shared_task(name="maintenance.update_subscription_daily", queue="maintenance")
def update_subscription_daily():
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        now = timezone.now()
        today = now.date()
        # Use timezone-aware datetime for DateTimeField comparisons
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        updated_count = 0

        active_users = User.objects.filter(
            is_premium=True, subscription_end_date__gte=start_of_today
        )

        for user in active_users:
            if user.subscription_start_date:
                days_subscribed = (today - user.subscription_start_date.date()).days + 1
                if user.consecutive_subscription_days != days_subscribed:
                    user.consecutive_subscription_days = days_subscribed
                    user.save(update_fields=["consecutive_subscription_days"])
                    updated_count += 1

        expired_users = User.objects.filter(
            is_premium=True, subscription_end_date__lt=start_of_today
        )

        for user in expired_users:
            if user.consecutive_subscription_days > 0 or user.is_premium:
                user.consecutive_subscription_days = 0
                user.is_premium = False
                user.save(update_fields=["consecutive_subscription_days", "is_premium"])
                updated_count += 1

        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")

        logger.info(
            "Daily subscription update completed",
            extra={
                "event": "update_subscription_daily",
                "updated_count": updated_count,
                "active_users": len(active_users),
                "expired_users": len(expired_users),
            },
        )

        return {
            "status": "success",
            "updated_count": updated_count,
            "active_users": len(active_users),
            "expired_users": len(expired_users),
        }

    except Exception as exc:
        logger.error(
            f"Daily subscription update failed: {str(exc)}",
            exc_info=True,
            extra={"event": "update_subscription_daily_failed"},
        )
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


@shared_task(name="maintenance.cleanup_stuck_operations", queue="maintenance")
def cleanup_stuck_operations(max_age_hours: int = 24):
    """
    Clean up stuck OperationRun records.

    Marks operations stuck in 'running' or 'started' status as 'abandoned'
    if they are older than max_age_hours.

    Args:
        max_age_hours: Maximum age in hours before marking as abandoned (default: 24)
    """
    try:
        from datetime import timedelta

        from src.users.models import OperationRun

        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

        stuck_operations = OperationRun.objects.filter(
            status__in=["running", "started"], created_at__lt=cutoff_time
        )

        updated_count = stuck_operations.update(
            status="abandoned",
            finished_at=timezone.now(),
            error_type="TimeoutError",
            error_message="Operation abandoned - exceeded maximum processing time",
        )

        logger.info(
            f"Cleanup stuck operations completed: {updated_count} operations marked as abandoned",
            extra={
                "event": "cleanup_stuck_operations",
                "updated_count": updated_count,
                "max_age_hours": max_age_hours,
            },
        )

        return {"status": "success", "updated_count": updated_count}

    except Exception as exc:
        logger.error(
            f"Cleanup stuck operations failed: {str(exc)}",
            exc_info=True,
            extra={"event": "cleanup_stuck_operations_failed"},
        )
        return {"status": "error", "message": str(exc)}


@shared_task(name="maintenance.cleanup_old_operations", queue="maintenance")
def cleanup_old_operations(retention_days: int = 365):
    """
    Delete old OperationRun records with export.

    Exports operation records to JSON before deletion, then removes records
    older than retention_days to keep database size manageable.

    Args:
        retention_days: Number of days to retain operation records (default: 365)
    """
    try:
        import json
        from datetime import timedelta
        from pathlib import Path

        from src.users.models import OperationRun

        cutoff_time = timezone.now() - timedelta(days=retention_days)

        old_operations = OperationRun.objects.filter(created_at__lt=cutoff_time)
        deleted_count = old_operations.count()

        if deleted_count > 0:
            # Export to JSON before deletion
            export_dir = Path("/app/logs/operation_exports")
            export_dir.mkdir(parents=True, exist_ok=True)

            export_file = (
                export_dir
                / f"operations_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            # Prepare data for export
            export_data = []
            for op in old_operations.values(
                "id",
                "conversion_type",
                "status",
                "user_id",
                "is_premium",
                "created_at",
                "completed_at",
                "duration_ms",
                "file_size_bytes",
                "error_message",
            ):
                # Convert datetime to string for JSON serialization
                op["created_at"] = (
                    op["created_at"].isoformat() if op["created_at"] else None
                )
                op["completed_at"] = (
                    op["completed_at"].isoformat() if op["completed_at"] else None
                )
                export_data.append(op)

            # Write to file
            with open(export_file, "w") as f:
                json.dump(
                    {
                        "export_date": timezone.now().isoformat(),
                        "retention_days": retention_days,
                        "records_count": deleted_count,
                        "operations": export_data,
                    },
                    f,
                    indent=2,
                )

            logger.info(
                f"Exported {deleted_count} operations to {export_file}",
                extra={
                    "event": "operations_exported",
                    "count": deleted_count,
                    "file": str(export_file),
                },
            )

            # Now delete
            old_operations.delete()

            logger.info(
                f"Cleanup old operations completed: {deleted_count} operations deleted",
                extra={
                    "event": "cleanup_old_operations",
                    "deleted_count": deleted_count,
                    "retention_days": retention_days,
                    "export_file": str(export_file),
                },
            )

            return {
                "status": "success",
                "deleted_count": deleted_count,
                "export_file": str(export_file),
            }
        else:
            logger.info(
                "No old operations to cleanup",
                extra={
                    "event": "cleanup_old_operations",
                    "retention_days": retention_days,
                },
            )
            return {"status": "success", "deleted_count": 0}

    except Exception as exc:
        logger.error(
            f"Cleanup old operations failed: {str(exc)}",
            exc_info=True,
            extra={"event": "cleanup_old_operations_failed"},
        )
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
