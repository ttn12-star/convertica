"""Users app configuration."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.users"
    verbose_name = "Users"

    def ready(self):
        """Import signals when app is ready."""
        from . import signals  # noqa: F401
        from .runtime_settings import apply_cached_runtime_settings

        apply_cached_runtime_settings()
