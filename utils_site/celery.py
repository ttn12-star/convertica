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

    # Also autodiscover from our custom tasks package
    app.autodiscover_tasks(["src.tasks"])

    # Celery configuration
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
        # Task routing - all conversion tasks go to same queue for simplicity on small server
        task_routes={
            "pdf_conversion.*": {"queue": "celery"},
            "src.tasks.pdf_conversion.*": {"queue": "celery"},
            "src.tasks.maintenance.*": {"queue": "maintenance"},
            "maintenance.*": {"queue": "maintenance"},
            "email.*": {"queue": "default"},
        },
        # Default queue for unrouted tasks
        task_default_queue="celery",
        # Worker settings - optimized for 1 vCPU / 2GB server
        worker_prefetch_multiplier=1,  # Process one task at a time (prevents memory issues)
        worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (free memory)
        worker_max_memory_per_child=300000,  # 300MB per worker child
        # Task execution settings
        task_acks_late=True,  # Acknowledge tasks after completion
        task_reject_on_worker_lost=True,  # Reject tasks if worker dies
        # Result expiration - keep results for 2 hours for async download
        result_expires=7200,  # Results expire after 2 hours
        # Task time limits - allow up to 10 minutes for heavy conversions
        task_time_limit=600,  # Hard time limit: 10 minutes
        task_soft_time_limit=540,  # Soft time limit: 9 minutes
        # Retry settings - only for specific recoverable errors, NOT timeouts
        task_default_retry_delay=30,  # 30 seconds between retries
        task_max_retries=2,  # Maximum 2 retries (to avoid queue backlog)
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
