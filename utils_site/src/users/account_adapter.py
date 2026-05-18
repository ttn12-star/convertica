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


class EmailDeliveryError(Exception):
    """Raised when SMTP delivery fails for infra reasons.

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
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning(
                "Email delivery failed: %s",
                exc,
                extra={
                    "event": "email_delivery_failed",
                    "email_template": template_prefix,
                    "email_host": getattr(settings, "EMAIL_HOST", ""),
                    "email_port": getattr(settings, "EMAIL_PORT", ""),
                },
            )
            raise EmailDeliveryError(
                "Email service is temporarily unavailable. "
                "Please try again in a few minutes."
            ) from exc
