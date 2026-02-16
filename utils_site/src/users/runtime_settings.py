"""Runtime settings overrides configurable from Django admin."""

from __future__ import annotations

from threading import Lock
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError

RUNTIME_SETTINGS_CACHE_KEY = "runtime_settings:active_overrides:v1"

_runtime_lock = Lock()
_MISSING = object()
_original_values: dict[str, Any] = {}
_active_override_keys: set[str] = set()

# Explicitly sensitive keys that must never be editable in admin.
SENSITIVE_EXACT_KEYS = {
    "SECRET_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "TURNSTILE_SECRET_KEY",
    "DATABASE_PASSWORD",
    "EMAIL_HOST_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "VAPID_PRIVATE_KEY",
}

SENSITIVE_PREFIXES = (
    "SECRET_",
    "PRIVATE_",
)

SENSITIVE_SUFFIXES = (
    "_PASSWORD",
    "_SECRET",
    "_SECRET_KEY",
    "_PRIVATE_KEY",
    "_TOKEN",
)

SENSITIVE_FRAGMENTS = (
    "_PASSWORD_",
    "_SECRET_",
    "_PRIVATE_",
    "_TOKEN_",
)


def is_sensitive_setting_key(key: str) -> bool:
    """Return True if setting key appears to contain secrets."""
    normalized = (key or "").strip().upper()
    if not normalized:
        return True
    if normalized in SENSITIVE_EXACT_KEYS:
        return True
    if normalized.startswith(SENSITIVE_PREFIXES):
        return True
    if normalized.endswith(SENSITIVE_SUFFIXES):
        return True
    return any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS)


def get_active_runtime_overrides() -> dict[str, Any]:
    """Load active runtime setting overrides from cache/database."""
    cached = cache.get(RUNTIME_SETTINGS_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        from .models import RuntimeSetting

        overrides = {
            row["key"]: row["value"]
            for row in RuntimeSetting.objects.filter(is_active=True).values(
                "key", "value"
            )
            if not is_sensitive_setting_key(row["key"])
        }
    except (OperationalError, ProgrammingError):
        # DB might be unavailable during startup/migrations.
        overrides = {}

    cache.set(RUNTIME_SETTINGS_CACHE_KEY, overrides, timeout=None)
    return overrides


def invalidate_runtime_settings_cache() -> None:
    """Invalidate cached runtime settings overrides."""
    cache.delete(RUNTIME_SETTINGS_CACHE_KEY)


def _refresh_dependent_modules() -> None:
    """Refresh modules that cache settings at import time."""
    try:
        from src.api import conversion_limits

        conversion_limits.reload_from_settings()
    except Exception:
        # Keep request handling resilient if optional modules are unavailable.
        return


def _apply_overrides(overrides: dict[str, Any]) -> None:
    current_keys = set(overrides)
    with _runtime_lock:
        managed_keys = _active_override_keys | current_keys

        for key in managed_keys:
            if key not in _original_values:
                _original_values[key] = getattr(settings, key, _MISSING)

        # Restore original values for keys no longer overridden.
        for key in _active_override_keys - current_keys:
            original = _original_values.get(key, _MISSING)
            if original is _MISSING:
                if hasattr(settings, key):
                    delattr(settings, key)
            else:
                setattr(settings, key, original)

        # Apply current overrides.
        for key, value in overrides.items():
            setattr(settings, key, value)

        _active_override_keys.clear()
        _active_override_keys.update(current_keys)

    _refresh_dependent_modules()


def apply_runtime_settings() -> None:
    """Apply active runtime overrides to django.conf.settings."""
    overrides = get_active_runtime_overrides()
    _apply_overrides(overrides)


def apply_cached_runtime_settings() -> None:
    """Apply runtime overrides from cache only (without DB access)."""
    cached = cache.get(RUNTIME_SETTINGS_CACHE_KEY)
    if isinstance(cached, dict):
        _apply_overrides(cached)


def refresh_runtime_settings() -> None:
    """Refresh cache and immediately apply runtime overrides."""
    invalidate_runtime_settings_cache()
    apply_runtime_settings()
