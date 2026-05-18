"""Middleware for users app: runtime settings + SMTP-failure 503 mapping."""

import logging

from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .account_adapter import EmailDeliveryError
from .runtime_settings import apply_runtime_settings

logger = logging.getLogger(__name__)


class RuntimeSettingsMiddleware:
    """Apply runtime admin-configured settings before request handling."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        apply_runtime_settings()
        return self.get_response(request)


class EmailDeliveryErrorMiddleware:
    """Render a 503 page when ``EmailDeliveryError`` propagates out of a view.

    Allauth's password-reset/signup views call ``adapter.send_mail`` deep in
    their form ``save()``; without this, an SMTP infra outage surfaces as a
    500 white page. ``CustomAccountAdapter.send_mail`` raises the controlled
    ``EmailDeliveryError``; this middleware turns it into a user-facing 503
    so live users see something other than a generic crash.

    Logging is intentionally not done here — the adapter already logs at
    warning level with full context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, EmailDeliveryError):
            return None
        try:
            html = render_to_string(
                "503.html",
                {"email_error_message": str(exception)},
                request=request,
            )
        except TemplateDoesNotExist:
            html = f"<h1>503 Service Unavailable</h1><p>{exception}</p>"
        return HttpResponse(html, status=503, content_type="text/html")
