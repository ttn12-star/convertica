"""
Celery configuration for Convertica.

This module configures Celery for asynchronous task processing.
Celery is used for handling PDF conversions and other heavy operations
to prevent blocking the main request/response cycle.
"""

import os

try:
    from celery import Celery
    from django.conf import settings

    # Set the default Django settings module for the 'celery' program.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utils_site.settings")

    app = Celery("convertica")

    # Using a string here means the worker doesn't have to serialize
    # the configuration object to child processes.
    # - namespace='CELERY' means all celery-related configuration keys
    #   should have a `CELERY_` prefix.
    app.config_from_object("django.conf:settings", namespace="CELERY")

    # Load task modules from all registered Django apps.
    app.autodiscover_tasks()

    # Explicitly register tasks from src.tasks package
    # These are not in standard Django app structure so autodiscover won't find them
    # Import AFTER app is created so tasks are registered with this app
    from src.tasks import email  # noqa: F401
    from src.tasks import maintenance  # noqa: F401
    from src.tasks import pdf_conversion  # noqa: F401
    from src.tasks import user_cleanup  # noqa: F401

    # Also autodiscover from our custom tasks package
    app.autodiscover_tasks(["src.tasks"])

    # Celery configuration - optimized for 4GB server with premium queues
    app.conf.update(
        # Broker settings
        broker_url=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=os.environ.get(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
        ),
        # Broker connection retry on startup (for Celery 6.0+ compatibility)
        broker_connection_retry_on_startup=True,
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Task routing
        task_routes={
            # Maintenance tasks to separate queue
            "src.tasks.maintenance.*": {"queue": "maintenance"},
            "maintenance.*": {"queue": "maintenance"},
            # Email tasks to default queue
            "email.*": {"queue": "default"},
            # Telegram tasks to default queue
            "telegram.*": {"queue": "default"},
        },
        # Queue definitions - regular gets priority
        task_default_queue="regular",
        task_queues={
            "regular": {
                "exchange": "regular",
                "routing_key": "regular",
            },
            "premium": {
                "exchange": "premium",
                "routing_key": "premium",
            },
            "maintenance": {
                "exchange": "maintenance",
                "routing_key": "maintenance",
            },
            "default": {
                "exchange": "default",
                "routing_key": "default",
            },
        },
        # Worker settings - optimized for premium priority
        worker_prefetch_multiplier=1,  # Process one task at a time (prevents task hoarding)
        worker_max_tasks_per_child=40,  # Reduced for memory stability
        worker_max_memory_per_child=250000,  # 250MB per worker child
        worker_pool="solo",  # Use solo pool for memory efficiency on small servers
        # Task execution settings
        task_acks_late=True,  # Acknowledge tasks after completion (allows task requeue on failure)
        task_reject_on_worker_lost=True,  # Reject tasks if worker dies
        # Priority settings - premium tasks get higher priority
        task_default_priority=5,  # Default priority for regular tasks
        task_inherit_parent_priority=True,  # Child tasks inherit parent priority
        # Result expiration - keep results for 2 hours for async download
        result_expires=7200,  # Results expire after 2 hours
        # Task time limits - reduced for memory stability
        task_time_limit=480,  # Hard time limit: 8 minutes (reduced from 10)
        task_soft_time_limit=420,  # Soft time limit: 7 minutes (reduced from 9)
        # Retry settings - conservative for memory stability
        task_default_retry_delay=60,  # 60 seconds between retries (increased)
        task_max_retries=1,  # Maximum 1 retry (reduced from 2)
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        # Track task state during execution (for progress reporting)
        task_track_started=True,
        # Beat schedule for periodic tasks
        beat_schedule={
            "cleanup-async-temp-files": {
                "task": "maintenance.cleanup_async_temp_files",
                "schedule": 1800.0,  # Every 30 minutes
                "kwargs": {"max_age_seconds": 3600},  # Clean files older than 1 hour
            },
            "cleanup-temp-files": {
                "task": "maintenance.cleanup_temp_files",
                "schedule": 3600.0,  # Every hour
            },
            "memory-cleanup": {
                "task": "maintenance.memory_cleanup",
                "schedule": 900.0,  # Every 15 minutes for 4GB servers
            },
            "update-subscription-daily": {
                "task": "maintenance.update_subscription_daily",
                "schedule": 86400.0,  # Every 24 hours
            },
            "cleanup-stuck-operations": {
                "task": "maintenance.cleanup_stuck_operations",
                "schedule": 3600.0,  # Every hour
                "kwargs": {"max_age_hours": 1},  # Mark as abandoned after 1 hour
            },
            "cleanup-old-operations": {
                "task": "maintenance.cleanup_old_operations",
                "schedule": 86400.0,  # Every 24 hours
                "kwargs": {"retention_days": 365},  # Keep operations for 1 year
            },
        },
    )

    @app.task(bind=True, ignore_result=True)
    def debug_task(self):
        """Debug task to test Celery setup."""
        # Log request details for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Request: {self.request!r}")

except ImportError:
    # Celery is not installed, create a dummy app
    app = None
