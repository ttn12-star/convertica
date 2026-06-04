"""
Premium user utilities for enhanced features.

Provides helper functions for checking premium status and applying
premium-specific features like batch processing and unlimited limits.
"""

from django.core.cache import cache

_PREMIUM_CACHE_TTL = 60  # seconds — short, so a webhook flip propagates quickly


def is_premium_active(user) -> bool:
    """Check if user has active premium subscription.

    Verifies both the is_premium flag (admin/webhook-driven) and the
    subscription_end_date via the model's is_subscription_active() method,
    so an expired subscription that hasn't yet been reconciled by the
    payment provider's webhook does not silently grant premium.

    Caches the result per-user for _PREMIUM_CACHE_TTL seconds to avoid
    hitting the DB on every request — the cache is invalidated when the
    User model is saved (see users/models.save).
    """
    if not user or not user.is_authenticated:
        return False

    cache_key = f"user_premium_active:{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    if not hasattr(user, "is_premium") or not user.is_premium:
        cache.set(cache_key, False, _PREMIUM_CACHE_TTL)
        return False

    if hasattr(user, "is_subscription_active"):
        result = bool(user.is_subscription_active())
    else:
        result = False

    cache.set(cache_key, result, _PREMIUM_CACHE_TTL)
    return result


def ocr_premium_gate_message(user, payments_enabled: bool) -> str | None:
    """Return an OCR-denial message, or None if the user may use OCR.

    OCR is a premium-only feature. The same gate is applied on the sync,
    batch and async conversion paths; centralising the wording here keeps
    them from drifting apart. Messages mirror BaseConversionAPIView.post.
    """
    if user.is_authenticated and is_premium_active(user):
        return None

    if not user.is_authenticated:
        return (
            "OCR is a premium feature. Please log in and upgrade to Premium."
            if payments_enabled
            else "OCR feature is not available. Please log in to use this feature."
        )

    return (
        "OCR is a premium feature. Upgrade to Premium to enable OCR processing."
        if payments_enabled
        else "OCR feature is not available at this time."
    )


def get_max_batch_files(user) -> int:
    """Get maximum number of files allowed in batch processing.

    Args:
        user: Django user object

    Returns:
        Maximum batch size, read from settings (premium vs free).
    """
    from django.conf import settings

    if is_premium_active(user):
        return getattr(settings, "MAX_BATCH_FILES_PREMIUM", 10)
    return getattr(settings, "MAX_BATCH_FILES_FREE", 1)


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
                    "Choose monthly or yearly Premium plans.",
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

    from django.conf import settings

    return {
        "is_premium": is_premium,
        "max_file_size_mb": (
            settings.MAX_FILE_SIZE_PREMIUM / (1024 * 1024)
            if is_premium
            else settings.MAX_FILE_SIZE_FREE / (1024 * 1024)
        ),
        "max_pages": (
            settings.MAX_PDF_PAGES_PREMIUM
            if is_premium
            else settings.MAX_PDF_PAGES_FREE
        ),
        "max_batch_files": (
            settings.MAX_BATCH_FILES_PREMIUM
            if is_premium
            else settings.MAX_BATCH_FILES_FREE
        ),
        "priority_queue": is_premium,
        "unlimited_conversions": is_premium,
        "no_ads": is_premium,
        "ocr_enabled": is_premium,
        "api_access": is_premium,
    }
