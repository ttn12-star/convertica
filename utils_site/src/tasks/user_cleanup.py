"""
Celery tasks for user account cleanup and maintenance.
"""

from celery import shared_task
from django.utils import timezone

from ..api.logging_utils import get_logger

logger = get_logger(__name__)


@shared_task(name="user_cleanup.delete_unverified_accounts")
def delete_unverified_accounts():
    """
    Delete user accounts that haven't verified their email within 30 days.

    This task runs daily and removes accounts that:
    - Have not verified their email address
    - Were created more than 30 days ago
    - Are not premium users (to avoid accidental deletion of paying customers)
    """
    from allauth.account.models import EmailAddress
    from django.contrib.auth import get_user_model

    User = get_user_model()
    cutoff_date = timezone.now() - timezone.timedelta(days=30)

    # Find users without verified email addresses
    unverified_users = User.objects.filter(
        date_joined__lt=cutoff_date,
        is_premium=False,  # Don't delete premium users
        is_staff=False,  # Don't delete staff
        is_superuser=False,  # Don't delete superusers
    ).exclude(
        # Exclude users who have at least one verified email
        id__in=EmailAddress.objects.filter(verified=True).values_list(
            "user_id", flat=True
        )
    )

    deleted_count = 0
    for user in unverified_users:
        email = user.email
        user_id = user.id
        days_old = (timezone.now() - user.date_joined).days

        try:
            user.delete()
            deleted_count += 1
            logger.info(
                f"Deleted unverified account: {email} (ID: {user_id}, {days_old} days old)",
                extra={
                    "event": "unverified_account_deleted",
                    "user_id": user_id,
                    "email": email,
                    "days_old": days_old,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to delete unverified account: {email}",
                extra={
                    "event": "unverified_account_deletion_failed",
                    "user_id": user_id,
                    "email": email,
                    "error": str(e),
                },
            )

    logger.info(
        f"Unverified account cleanup completed: {deleted_count} accounts deleted",
        extra={
            "event": "unverified_account_cleanup_completed",
            "deleted_count": deleted_count,
        },
    )

    return deleted_count
