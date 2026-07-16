"""Daily conversion quota for tools opened up from premium-only to free.

HEIC->JPG, PDF->Markdown and EPUB<->PDF used to be premium-only. They are now
usable by everyone under a modest per-day cap so they can rank in search and
feed the funnel, while batch mode, large files and OCR stay premium. Premium
users are unlimited.

ponytail: single shared daily bucket per identity (authenticated user pk, else
client IP), backed by the cache with a 24h TTL. Counts attempts, not successes
-- a failed upload still consumes one unit (same philosophy as the existing IP
spam counter in spam_protection). Split into per-operation buckets if one tool
ever needs its own budget.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from .client_ip import get_client_ip
from .premium_utils import is_premium_active

_WINDOW_SECONDS = 24 * 60 * 60


def _identity_and_limit(request) -> tuple[str, int]:
    """Return (cache identity, daily limit) for the caller.

    Authenticated users are keyed by pk and get the (higher) registered limit;
    anonymous callers are keyed by trusted client IP and get the anon limit.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"u:{user.pk}", getattr(settings, "DAILY_QUOTA_REGISTERED", 5)
    ip = get_client_ip(request) or "unknown"
    return f"ip:{ip}", getattr(settings, "DAILY_QUOTA_ANON", 2)


def _limit_message(is_authenticated: bool, limit: int) -> str:
    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
    if not is_authenticated:
        if payments_enabled:
            return _(
                "You've reached the free daily limit (%(limit)d/day). Log in for a "
                "higher limit, or upgrade to Premium for unlimited conversions."
            ) % {"limit": limit}
        return _(
            "You've reached the free daily limit (%(limit)d/day). "
            "Log in for a higher limit."
        ) % {"limit": limit}
    if payments_enabled:
        return _(
            "You've reached your daily limit (%(limit)d/day). "
            "Upgrade to Premium for unlimited conversions."
        ) % {"limit": limit}
    return _("You've reached your daily limit (%(limit)d/day).") % {"limit": limit}


def try_consume_daily_quota(request) -> tuple[bool, str | None]:
    """Consume one unit of the caller's daily quota.

    Returns (allowed, error_message). Premium users are always allowed and never
    consume quota. The current request is counted even when it is rejected, which
    bounds abuse at the cost of a rejected upload still burning one unit.
    """
    user = getattr(request, "user", None)
    if is_premium_active(user):
        return True, None

    identity, limit = _identity_and_limit(request)
    key = f"daily_quota:{identity}"
    # add() writes the key with its TTL only when absent, so the subsequent
    # incr() keeps the original 24h window instead of resetting it each call.
    cache.add(key, 0, _WINDOW_SECONDS)
    try:
        used = cache.incr(key)
    except ValueError:
        # Key expired between add() and incr() -- start a fresh window.
        cache.set(key, 1, _WINDOW_SECONDS)
        used = 1

    if used > limit:
        is_auth = bool(user is not None and getattr(user, "is_authenticated", False))
        return False, _limit_message(is_auth, limit)
    return True, None
