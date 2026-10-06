"""Middleware for users app: runtime settings + SMTP-failure 503 mapping."""

import logging
import time

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


class SlidingSessionMiddleware:
    """Keep the 30-day session sliding, writing it at most once a day.

    SESSION_SAVE_EVERY_REQUEST did the sliding by saving the session on every
    request of a logged-in user: an UPDATE per status poll and page view, and
    concurrent requests (a poll plus an action) overwrote each other's session
    data. Touching a timestamp once a day marks the session modified, so
    Django saves it with a fresh expiry; the window moves in one-day steps.
    Must sit inside SessionMiddleware, which saves on the way out.
    """

    REFRESH_SECONDS = 86400

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        session = getattr(request, "session", None)
        # Logged-in sessions only: no cookie means no key (nothing loaded or
        # written), and an expired or forged cookie loads as empty, so it
        # gets no fresh session row out of this.
        if session is not None and session.session_key and session.get("_auth_user_id"):
            now = int(time.time())
            if now - session.get("_slid_at", 0) > self.REFRESH_SECONDS:
                session["_slid_at"] = now
        return response
