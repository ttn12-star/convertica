"""
Celery configuration for Convertica.

This module configures Celery for asynchronous task processing.
Celery is used for handling PDF conversions and other heavy operations
to prevent blocking the main request/response cycle.
"""

import os

try:
    from celery import Celery
    from celery.signals import task_prerun
    from django.conf import settings

    # Set the default Django settings module for the 'celery' program.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utils_site.settings")

    app = Celery("convertica")

    # Using a string here means the worker doesn't have to serialize
    # the configuration object to child processes.
    # - namespace='CELERY' means all celery-related configuration keys
    #   should have a `CELERY_` prefix.
    # IMPORTANT: This loads CELERY_BEAT_SCHEDULE from settings.py
    # The beat_schedule defined below in app.conf.update() will be OVERRIDDEN
    # by settings.CELERY_BEAT_SCHEDULE - always edit settings.py for beat schedule
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
        # Queue definitions.
        # "fast" queue: PDF-only operations that complete in <15s (compress, split,
        #   merge, rotate, crop, watermark, page numbers, extract/remove pages).
        #   The regular worker listens to fast FIRST so these tasks don't wait
        #   behind long Word→PDF / OCR conversions sitting in "regular".
        # "regular" queue: heavy multi-format conversions (word_to_pdf, pdf_to_word,
        #   pdf_to_excel, pdf_to_markdown, epub conversions, etc.)
        # "premium" queue: same heavy operations but for subscribed users.
        task_default_queue="regular",
        task_queues={
            "fast": {
                "exchange": "fast",
                "routing_key": "fast",
            },
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
        worker_max_tasks_per_child=50,  # Aligned with docker-compose.prod.yml for memory stability
        worker_max_memory_per_child=250000,  # 250MB per worker child
        worker_pool="prefork",  # Default pool; docker-compose CLI --pool flag overrides per worker type
        # Production regular worker: prefork (concurrency=2)
        # Production premium worker: solo (concurrency=1)
        # Dev workers: solo (concurrency=1)
        # Task execution settings
        task_acks_late=True,  # Acknowledge tasks after completion (allows task requeue on failure)
        task_reject_on_worker_lost=True,  # Reject tasks if worker dies
        # Priority settings - premium tasks get higher priority
        task_default_priority=5,  # Default priority for regular tasks
        task_inherit_parent_priority=True,  # Child tasks inherit parent priority
        # Result expiration — bumped to 24h so users returning later in the
        # day can still download their result instead of hitting a 404.
        result_expires=86400,
        # Task time limits - reduced for memory stability
        task_time_limit=480,  # Hard time limit: 8 minutes (reduced from 10)
        task_soft_time_limit=420,  # Soft time limit: 7 minutes (reduced from 9)
        # Retry settings — exponential backoff with jitter avoids the thundering
        # herd that fixed 60s delays would cause if unoserver/Stripe/SMTP is
        # briefly unhealthy and many tasks retry at the same instant.
        task_default_retry_delay=60,
        task_max_retries=1,
        task_retry_backoff=True,
        task_retry_backoff_max=600,  # cap at 10 min
        task_retry_jitter=True,
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        # Track task state during execution (for progress reporting)
        task_track_started=True,
        # NOTE: Beat schedule is configured in settings.CELERY_BEAT_SCHEDULE
        # This is loaded via app.config_from_object() with namespace='CELERY'
    )

    @app.task(bind=True, ignore_result=True)
    def debug_task(self):
        """Debug task to test Celery setup."""
        # Log request details for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Request: {self.request!r}")

    @task_prerun.connect
    def apply_runtime_settings_before_task(*args, **kwargs):
        """Ensure admin runtime setting overrides are applied for worker tasks."""
        try:
            from src.users.runtime_settings import apply_runtime_settings

            apply_runtime_settings()
        except Exception:
            # Keep task execution resilient if runtime settings are unavailable.
            return

except ImportError:
    # Celery is not installed, create a dummy app
    app = None
