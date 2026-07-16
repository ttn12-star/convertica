"""Global daily conversion quota: anon < registered < premium (unlimited).

One shared bucket per identity across ALL tools (the funnel lever), enforced
centrally by ``DailyQuotaMiddleware`` (api/middleware.py) on every conversion
POST. Anonymous callers get ``DAILY_QUOTA_ANON`` (10) per day, registered
users ``DAILY_QUOTA_REGISTERED`` (40), premium users are unlimited.

Semantics (deliberate, keep in sync with the middleware):
- Calendar-day UTC window — the key embeds the date, so "resets tomorrow" is
  literally true and easy to communicate, unlike a rolling 24h window.
- Counts SUCCESSES only (2xx responses) — a rejected/invalid upload does not
  burn a unit; abuse is bounded by the separate hourly IP limits and
  spam_protection layers, which do count attempts.

ponytail: identity = authenticated user pk, else client IP. IP-keying means
incognito does not reset the bucket, but an office NAT shares one; add a
cookie+IP dual bucket only if NAT collisions show up in support.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from .client_ip import get_client_ip

# A day plus slack so a bucket created at 00:01 UTC comfortably outlives its day.
_TTL_SECONDS = 25 * 60 * 60


def _identity_and_limit(request) -> tuple[str, int]:
    """Return (cache identity, daily limit) for the caller.

    Authenticated users are keyed by pk and get the (higher) registered limit;
    anonymous callers are keyed by trusted client IP and get the anon limit.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"u:{user.pk}", getattr(settings, "DAILY_QUOTA_REGISTERED", 40)
    ip = get_client_ip(request) or "unknown"
    return f"ip:{ip}", getattr(settings, "DAILY_QUOTA_ANON", 10)


def _cache_key(identity: str) -> str:
    return f"daily_quota:{identity}:{timezone.now().date().isoformat()}"


def get_quota_state(request) -> tuple[str, int, int]:
    """Return (cache_key, limit, used_today) for the caller. Cheap: one GET."""
    identity, limit = _identity_and_limit(request)
    key = _cache_key(identity)
    try:
        used = int(cache.get(key) or 0)
    except Exception:
        used = 0  # cache down -> fail open
    return key, limit, used


def consume_quota_unit(key: str) -> int:
    """Count one successful conversion; return the new used total (best effort)."""
    try:
        cache.add(key, 0, _TTL_SECONDS)
        return cache.incr(key)
    except Exception:
        return 0  # never fail a successful conversion over quota bookkeeping


def quota_limit_message(is_authenticated: bool, limit: int) -> str:
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
