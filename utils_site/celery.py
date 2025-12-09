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
    import src.tasks.email  # noqa: F401
    import src.tasks.maintenance  # noqa: F401

    # Celery configuration
    app.conf.update(
        # Broker settings
        broker_url=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=os.environ.get(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
        ),
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Task routing
        task_routes={
            "src.tasks.pdf_conversion.*": {"queue": "pdf_conversion"},
            "src.tasks.pdf_processing.*": {"queue": "pdf_processing"},
            "src.tasks.maintenance.*": {"queue": "maintenance"},
            "email.*": {"queue": "default"},
        },
        # Worker settings
        worker_prefetch_multiplier=4,  # Prefetch 4 tasks at a time
        worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
        # Task execution settings
        task_acks_late=True,  # Acknowledge tasks after completion
        task_reject_on_worker_lost=True,  # Reject tasks if worker dies
        # Result expiration
        result_expires=3600,  # Results expire after 1 hour
        # Task time limits
        task_time_limit=600,  # Hard time limit: 10 minutes
        task_soft_time_limit=540,  # Soft time limit: 9 minutes
        # Retry settings
        task_autoretry_for=(Exception,),
        task_retry_backoff=True,
        task_retry_backoff_max=600,  # Max retry delay: 10 minutes
        task_retry_jitter=True,
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
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
