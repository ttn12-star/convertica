"""DRF authentication backend for cvk_live_<prefix><secret> API keys.

Lookup flow:
  Authorization: Bearer cvk_live_<prefix:12><secret:32+>
  → strip "cvk_live_" namespace
  → split: prefix = first 12, secret = remainder
  → DB lookup by prefix (indexed), verify SHA-256 hash matches
  → check revoked_at is null
  → check user.is_subscription_active()
  → atomic-increment usage_this_month, compare to plan quota
  → AuthenticationFailed if over quota
"""

import hashlib
import hmac

from django.db.models import F
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from src.users.models import APIKey

PREFIX_NAMESPACE = "cvk_live_"


def _lookup_api_key(token: str):
    """Resolve a cvk_live_ token to its APIKey by prefix + hash + active flag.

    Shared by the DRF authenticator and the identity middleware so both apply
    the exact same validation. Raises AuthenticationFailed on malformed /
    unknown / mismatched / revoked keys. Does NOT check subscription/quota and
    does NOT charge — callers layer those on.
    """
    body = token.removeprefix(PREFIX_NAMESPACE)
    if len(body) < 13:
        raise AuthenticationFailed("Malformed API key")
    prefix = body[:12]

    try:
        key = APIKey.objects.select_related("user").get(prefix=prefix)
    except APIKey.DoesNotExist:
        raise AuthenticationFailed("Unknown API key")

    expected = hashlib.sha256(token.encode()).hexdigest()
    if not hmac.compare_digest(key.key_hash, expected):
        # Same prefix collision is astronomically rare, but treat as
        # unauthenticated either way.
        raise AuthenticationFailed("Invalid API key")

    if not key.is_active:
        raise AuthenticationFailed("API key revoked")

    return key


def resolve_api_key_user(request):
    """Best-effort identity for a cvk_live_ request — the User behind a valid,
    active-subscription API key, or None. NEVER raises, NEVER charges quota.

    DRF's APIKeyAuthentication only establishes identity inside the view
    (dispatch → initial), so earlier layers (RateLimitMiddleware, the
    dispatch-level `combined_rate_limit`, OperationRun analytics, DailyQuota)
    otherwise see AnonymousUser and treat a paying API caller as anonymous
    free-tier. This resolver lets those layers see the real premium identity.
    The result is memoized on the underlying Django request so we hit the DB
    at most once per request. Quota metering stays exclusively in
    APIKeyAuthentication.authenticate (charged once, in the view).
    """
    dj = getattr(request, "_request", request)
    if hasattr(dj, "_cvk_identity_user"):
        return dj._cvk_identity_user

    user = None
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if header.startswith("Bearer "):
        token = header.removeprefix("Bearer ").strip()
        if token.startswith(PREFIX_NAMESPACE):
            try:
                key = _lookup_api_key(token)
                if key.user.is_subscription_active():
                    user = key.user
            except Exception:
                user = None  # forged/expired keys stay anonymous here; DRF 401s them

    dj._cvk_identity_user = user
    return user


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        token = header.removeprefix(f"{self.keyword} ").strip()
        if not token.startswith(PREFIX_NAMESPACE):
            return None  # not an API key; let WebTokenAuth handle it

        key = _lookup_api_key(token)

        user = key.user
        if not user.is_subscription_active():
            raise AuthenticationFailed(
                "Subscription required for API access. Visit /pricing/."
            )

        quota = user.api_quota_per_month
        if quota == 0:
            raise AuthenticationFailed("Plan has no API quota")
        if key.usage_this_month >= quota:
            raise AuthenticationFailed(
                f"API quota exhausted ({key.usage_this_month}/{quota} this month)"
            )

        # CORS preflight carries no real work — never meter it.
        if request.method == "OPTIONS":
            return (user, key)

        # F() ensures concurrent calls don't lose counts.
        APIKey.objects.filter(pk=key.pk).update(
            usage_this_month=F("usage_this_month") + 1,
            last_used_at=timezone.now(),
        )
        # Reflect the increment on the in-memory object without a second round
        # trip — refresh_from_db here was a wasted query (the quota gate above
        # already ran against the pre-increment value).
        key.usage_this_month += 1

        # Mark the underlying request so APIKeyQuotaRefundMiddleware can refund
        # this unit if the request ultimately fails (non-2xx) — customers must
        # not be billed for rejected/errored conversions.
        django_request = getattr(request, "_request", request)
        django_request._cvk_api_key_charge = key.pk

        return (user, key)
