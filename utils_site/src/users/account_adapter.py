"""
Custom allauth account adapter for email verification redirects and
resilient SMTP delivery.
"""

import logging
import smtplib

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse

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
# HTTP API path (SendGrid via django-anymail): AnymailError covers both
# AnymailRequestsAPIError (4xx/5xx response from the ESP) and
# AnymailAPIError / AnymailRequestsAPIError / AnymailConnectionError.
_EMAIL_DELIVERY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    OSError,
    smtplib.SMTPException,
    AnymailError,
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
        """Translate SMTP/network failures into ``EmailDeliveryError``.

        Allauth flows (signup, password reset, resend-confirmation) all funnel
        through ``send_mail``. When the SMTP server is unreachable, default
        behaviour is to bubble ``OSError``/``SMTPException`` up as an
        unhandled exception, which Django renders as a 500 with no useful
        info for the user, and Sentry escalates as a real error.

        See CONVERTICA-50/51 (May 2026) — SMTP host briefly unreachable from
        prod containers; every email-sending request 500'd for live users.
        """
        try:
            return super().send_mail(template_prefix, email, context)
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
