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
    """
    Update subscription days for active users and deactivate expired subscriptions.

    This task only runs if PAYMENTS_ENABLED is True.
    """
    # Skip if payments/subscriptions are disabled
    if not getattr(settings, "PAYMENTS_ENABLED", True):
        logger.info(
            "Subscription update skipped - payments disabled",
            extra={"event": "update_subscription_daily_skipped"},
        )
        return {"status": "skipped", "reason": "payments_disabled"}

    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        now = timezone.now()
        today = now.date()
        # Use timezone-aware datetime for DateTimeField comparisons
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Update active users' subscription days using bulk_update
        active_users = list(
            User.objects.filter(
                is_premium=True, subscription_end_date__gte=start_of_today
            )
        )

        users_to_update_active = []
        for user in active_users:
            if user.subscription_start_date:
                days_subscribed = (today - user.subscription_start_date.date()).days + 1
                if user.consecutive_subscription_days != days_subscribed:
                    user.consecutive_subscription_days = days_subscribed
                    users_to_update_active.append(user)

        if users_to_update_active:
            User.objects.bulk_update(
                users_to_update_active,
                ["consecutive_subscription_days"],
                batch_size=500,
            )

        # Handle expired subscriptions using bulk_update
        expired_users = list(
            User.objects.filter(
                is_premium=True, subscription_end_date__lt=start_of_today
            )
        )

        users_to_update_expired = []
        for user in expired_users:
            if user.consecutive_subscription_days > 0 or user.is_premium:
                user.consecutive_subscription_days = 0
                user.is_premium = False
                users_to_update_expired.append(user)

        if users_to_update_expired:
            User.objects.bulk_update(
                users_to_update_expired,
                ["consecutive_subscription_days", "is_premium"],
                batch_size=500,
            )

        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")

        updated_active = len(users_to_update_active)
        updated_expired = len(users_to_update_expired)

        logger.info(
            "Daily subscription update completed",
            extra={
                "event": "update_subscription_daily",
                "updated_active": updated_active,
                "updated_expired": updated_expired,
                "total_active": len(active_users),
                "total_expired": len(expired_users),
            },
        )

        return {
            "status": "success",
            "updated_active": updated_active,
            "updated_expired": updated_expired,
            "total_active": len(active_users),
            "total_expired": len(expired_users),
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

        # Import background task checker
        from src.api.cancel_task_view import is_task_background

        # Iterate through task directories
        skipped_bg = 0
        for task_dir in async_dir.iterdir():
            if not task_dir.is_dir():
                continue

            try:
                # Skip background tasks (premium users' tasks still in progress)
                task_id = task_dir.name
                if is_task_background(task_id):
                    skipped_bg += 1
                    continue

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
            f"{size_freed_mb} MB freed, {skipped_bg} background tasks skipped"
        )

        return {
            "status": "success",
            "cleaned": cleaned_count,
            "size_freed_mb": size_freed_mb,
            "skipped_background": skipped_bg,
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
                "finished_at",
                "duration_ms",
                "input_size",
                "output_size",
                "error_message",
            ):
                # Convert datetime to string for JSON serialization
                op["created_at"] = (
                    op["created_at"].isoformat() if op["created_at"] else None
                )
                op["finished_at"] = (
                    op["finished_at"].isoformat() if op["finished_at"] else None
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


@shared_task(
    name="maintenance.retry_failed_webhooks",
    queue="maintenance",
    bind=True,
    max_retries=0,
)
def retry_failed_webhooks(self, max_age_hours: int = 24, max_retries: int = 3):
    """
    Retry failed Stripe webhook events.

    Finds webhook events with errors that are less than max_age_hours old
    and haven't exceeded max_retries, then attempts to reprocess them.

    This task only runs if PAYMENTS_ENABLED is True.

    Args:
        max_age_hours: Maximum age of events to retry (default: 24 hours)
        max_retries: Maximum number of retry attempts per event (default: 3)
    """
    # Skip if payments/subscriptions are disabled
    if not getattr(settings, "PAYMENTS_ENABLED", True):
        logger.info(
            "Webhook retry skipped - payments disabled",
            extra={"event": "retry_failed_webhooks_skipped"},
        )
        return {"status": "skipped", "reason": "payments_disabled"}

    try:
        from datetime import timedelta

        import stripe
        from src.users.models import StripeWebhookEvent

        # Skip if Stripe is not configured
        if not getattr(settings, "STRIPE_SECRET_KEY", None):
            logger.info("Stripe not configured, skipping webhook retry")
            return {"status": "skipped", "reason": "stripe_not_configured"}

        stripe.api_key = settings.STRIPE_SECRET_KEY

        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

        # Find failed events (have last_error, not currently processing)
        failed_events = StripeWebhookEvent.objects.filter(
            last_error__isnull=False,
            processing=False,
            created_at__gte=cutoff_time,
        ).exclude(last_error="")

        retried_count = 0
        success_count = 0
        still_failing = 0

        for webhook_event in failed_events:
            # Check retry count (stored in last_error as "Retry X: ...")
            retry_count = webhook_event.last_error.count("Retry ")
            if retry_count >= max_retries:
                continue

            try:
                # Mark as processing
                webhook_event.processing = True
                webhook_event.save(update_fields=["processing"])

                # Retrieve event from Stripe
                event = stripe.Event.retrieve(webhook_event.event_id)

                # Import handlers
                from src.payments.views import (
                    handle_charge_dispute_created,
                    handle_charge_refunded,
                    handle_checkout_session_completed,
                    handle_invoice_payment_failed,
                    handle_invoice_payment_succeeded,
                    handle_subscription_deleted,
                    handle_subscription_updated,
                )

                # Route to appropriate handler
                handlers = {
                    "checkout.session.completed": handle_checkout_session_completed,
                    "invoice.payment_succeeded": handle_invoice_payment_succeeded,
                    "invoice.payment_failed": handle_invoice_payment_failed,
                    "customer.subscription.created": handle_subscription_updated,
                    "customer.subscription.updated": handle_subscription_updated,
                    "customer.subscription.deleted": handle_subscription_deleted,
                    "charge.refunded": handle_charge_refunded,
                    "charge.dispute.created": handle_charge_dispute_created,
                }

                handler = handlers.get(event.type)
                if handler:
                    handler(event.data.object)
                    success_count += 1

                    # Clear error on success
                    webhook_event.last_error = ""
                    webhook_event.processed_at = timezone.now()

                retried_count += 1

            except Exception as e:
                # Update error with retry count
                webhook_event.last_error = (
                    f"Retry {retry_count + 1}: {str(e)[:500]}\n"
                    f"Previous: {webhook_event.last_error[:1000]}"
                )
                still_failing += 1
                logger.warning(
                    f"Webhook retry failed for {webhook_event.event_id}: {e}",
                    extra={
                        "event": "webhook_retry_failed",
                        "event_id": webhook_event.event_id,
                        "event_type": webhook_event.event_type,
                        "retry_count": retry_count + 1,
                    },
                )

            finally:
                webhook_event.processing = False
                webhook_event.save(
                    update_fields=["processing", "last_error", "processed_at"]
                )

        logger.info(
            f"Webhook retry completed: {retried_count} retried, "
            f"{success_count} succeeded, {still_failing} still failing",
            extra={
                "event": "webhook_retry_completed",
                "retried": retried_count,
                "succeeded": success_count,
                "still_failing": still_failing,
            },
        )

        return {
            "status": "success",
            "retried": retried_count,
            "succeeded": success_count,
            "still_failing": still_failing,
        }

    except Exception as exc:
        logger.error(
            f"Webhook retry task failed: {str(exc)}",
            exc_info=True,
            extra={"event": "webhook_retry_task_failed"},
        )
        return {"status": "error", "message": str(exc)}
