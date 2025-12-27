"""
Premium user utilities for enhanced features.

Provides helper functions for checking premium status and applying
premium-specific features like batch processing and unlimited limits.
"""


def is_premium_active(user) -> bool:
    """Check if user has active premium subscription.

    Args:
        user: Django user object

    Returns:
        True if user has active premium subscription
    """
    if not user or not user.is_authenticated:
        return False

    if not hasattr(user, "is_premium") or not user.is_premium:
        return False

    if hasattr(user, "is_subscription_active"):
        return user.is_subscription_active()

    return False


def get_max_batch_files(user) -> int:
    """Get maximum number of files allowed in batch processing.

    Args:
        user: Django user object

    Returns:
        Maximum batch size (10 for premium, 1 for free)
    """
    if is_premium_active(user):
        return 10  # Premium users can process up to 10 files at once
    return 1  # Free users can only process 1 file at a time


def can_use_batch_processing(user, file_count: int) -> tuple[bool, str | None]:
    """Check if user can process given number of files in batch.

    Args:
        user: Django user object
        file_count: Number of files to process

    Returns:
        Tuple of (can_process, error_message)
    """
    max_batch = get_max_batch_files(user)

    if file_count > max_batch:
        if max_batch == 1:
            # Check if payments are enabled
            from django.conf import settings

            payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)

            if payments_enabled:
                return (
                    False,
                    "Free users can only process 1 file at a time. "
                    "Upgrade to Premium to process up to 10 files at once! "
                    "Get 1-day Premium for just $1.",
                )
            else:
                return (
                    False,
                    "You can only process 1 file at a time.",
                )
        else:
            return (
                False,
                f"Maximum {max_batch} files allowed in batch processing. "
                f"You tried to process {file_count} files.",
            )

    return True, None


def get_premium_features(user) -> dict:
    """Get dictionary of premium features for user.

    Args:
        user: Django user object

    Returns:
        Dictionary with premium feature flags and limits
    """
    is_premium = is_premium_active(user)

    return {
        "is_premium": is_premium,
        "max_file_size_mb": 200 if is_premium else 25,
        "max_pages": 200 if is_premium else 30,  # Free: 30 pages, Premium: 200 pages
        "max_batch_files": 10 if is_premium else 1,
        "priority_queue": is_premium,
        "unlimited_conversions": is_premium,
        "no_ads": is_premium,
        "ocr_enabled": is_premium,
        "api_access": is_premium,
    }
