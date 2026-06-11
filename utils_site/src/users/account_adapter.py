"""
Custom allauth account adapter for email verification redirects and
resilient SMTP delivery.
"""

import logging
import smtplib

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse
from kombu.exceptions import OperationalError as KombuOperationalError
from src.tasks.email import send_account_email

logger = logging.getLogger(__name__)

# django-anymail isn't a hard dependency (the adapter still works on plain
# SMTP backends in dev), so import the exception lazily; if anymail isn't
# installed, AnymailError is set to a sentinel that ``isinstance(..., ...)``
# can never match.
try:
    from anymail.exceptions import AnymailError
except ImportError:  # pragma: no cover - anymail is in requirements.txt

    class AnymailError(Exception):  # type: ignore[no-redef]
        """Sentinel placeholder when django-anymail is not installed."""


# Exceptions we treat as "email infrastructure failed for reasons unrelated
# to user input or our own bug" — these get downgraded from 500 to 503.
# SMTP path: OSError (network unreachable / connection refused / timeout) +
# smtplib.SMTPException (auth failure / server reject).
# HTTP API path (Brevo via django-anymail): AnymailError covers
# AnymailRequestsAPIError (4xx/5xx response from the ESP) and the lower-
# level AnymailAPIError / AnymailConnectionError variants too.
_EMAIL_DELIVERY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    OSError,
    smtplib.SMTPException,
    AnymailError,
    # Broker (Redis) unreachable when handing the send off to Celery.
    KombuOperationalError,
)


class EmailDeliveryError(Exception):
    """Raised when email delivery fails for infra reasons.

    Caught by ``EmailDeliveryErrorMiddleware`` to render a 503 page instead
    of a 500 white screen. The message is user-safe (no internal details).
    """


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter: post-verification redirects + resilient SMTP."""

    def get_email_verification_redirect_url(self, email_address):
        """Redirect after email verification/confirmation."""
        user = getattr(email_address, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return reverse("users:profile")
        return reverse("users:login")

    def send_mail(self, template_prefix, email, context):
        """Render in-request, deliver via Celery, 503 on infra failure.

        Allauth flows (signup, password reset, resend-confirmation) all funnel
        through ``send_mail``. Rendering stays synchronous so template/context
        bugs still surface as 500s, but delivery is handed to the
        ``email.send_account_email`` task: ESP latency or an outage no longer
        ties up a gunicorn worker (EMAIL_TIMEOUT is 20s), and transient
        failures are retried in the background instead of erroring the user.

        Infra failures — broker unreachable, or SMTP/ESP errors propagating
        from an inline (eager-mode) send — are translated into the controlled
        ``EmailDeliveryError`` so the middleware renders a 503, not a 500.

        See CONVERTICA-50/51 (May 2026) — SMTP host briefly unreachable from
        prod containers; every email-sending request 500'd for live users.
        """
        msg = self.render_mail(template_prefix, email, context)
        html_body = None
        for alternative in getattr(msg, "alternatives", None) or ():
            if alternative[1] == "text/html":
                html_body = alternative[0]

        try:
            return send_account_email.delay(
                subject=msg.subject,
                body=msg.body,
                from_email=msg.from_email,
                to=list(msg.to),
                html_body=html_body,
            )
        except _EMAIL_DELIVERY_EXCEPTIONS as exc:
            logger.warning(
                "Email delivery failed: %s",
                exc,
                extra={
                    "event": "email_delivery_failed",
                    "email_template": template_prefix,
                    "email_backend": getattr(settings, "EMAIL_BACKEND", ""),
                    "email_host": getattr(settings, "EMAIL_HOST", ""),
                    "email_port": getattr(settings, "EMAIL_PORT", ""),
                },
            )
            raise EmailDeliveryError(
                "Email service is temporarily unavailable. "
                "Please try again in a few minutes."
            ) from exc
