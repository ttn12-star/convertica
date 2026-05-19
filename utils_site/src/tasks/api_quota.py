"""Celery beat tasks for API quota management."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="api_quota.reset_monthly")
def reset_api_quotas_monthly():
    """Zero out usage_this_month on all API keys.

    Run by Celery beat at 00:01 on the 1st of every month. Returns the
    number of rows updated for monitoring.
    """
    from src.users.models import APIKey  # local import — avoids AppRegistryNotReady

    now = timezone.now()
    updated = APIKey.objects.exclude(usage_this_month=0).update(
        usage_this_month=0,
        usage_reset_at=now,
    )
    logger.info("reset_api_quotas_monthly: zeroed %d keys", updated)
    return updated
