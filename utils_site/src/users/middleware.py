"""Middleware for dynamic runtime settings overrides."""

from .runtime_settings import apply_runtime_settings


class RuntimeSettingsMiddleware:
    """Apply runtime admin-configured settings before request handling."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        apply_runtime_settings()
        return self.get_response(request)
