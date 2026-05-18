"""Regression tests for the SMTP-failure handling path.

Covers the case that flooded Sentry as CONVERTICA-50/51 in May 2026:
the prod container briefly couldn't reach the SMTP host, every
allauth email-sending view (signup, password reset, resend-confirmation)
500'd for live users.

Two layers protect the path:

1. ``CustomAccountAdapter.send_mail`` translates ``OSError`` /
   ``smtplib.SMTPException`` into the controlled ``EmailDeliveryError``,
   logging a warning with the EMAIL_HOST/port context.
2. ``EmailDeliveryErrorMiddleware`` catches that exception in
   ``process_exception`` and renders a 503 instead of a 500.
"""

from __future__ import annotations

import smtplib
from unittest import mock

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from src.users.account_adapter import CustomAccountAdapter, EmailDeliveryError
from src.users.middleware import EmailDeliveryErrorMiddleware

from utils_site.settings import _default_email_backend


@override_settings(EMAIL_HOST="smtp.example.test", EMAIL_PORT=587)
class CustomAccountAdapterSendMailTests(SimpleTestCase):
    """``send_mail`` must convert SMTP/OS errors into ``EmailDeliveryError``."""

    def _adapter(self):
        return CustomAccountAdapter()

    def test_oserror_raised_by_super_is_translated(self):
        adapter = self._adapter()
        boom = OSError(101, "Network is unreachable")

        with (
            mock.patch.object(
                CustomAccountAdapter.__mro__[1], "send_mail", side_effect=boom
            ) as super_send,
            self.assertLogs("src.users.account_adapter", level="WARNING") as captured,
            self.assertRaises(EmailDeliveryError) as exc_ctx,
        ):
            adapter.send_mail("account/email/email_confirmation", "x@y", {})

        super_send.assert_called_once()
        # __cause__ preserved for traceability in Sentry.
        self.assertIs(exc_ctx.exception.__cause__, boom)
        # Warning must include enough context to debug the SMTP outage.
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertIn("Email delivery failed", record.getMessage())
        self.assertEqual(record.event, "email_delivery_failed")
        self.assertEqual(record.email_host, "smtp.example.test")
        self.assertEqual(record.email_port, 587)

    def test_smtp_exception_is_translated(self):
        adapter = self._adapter()
        boom = smtplib.SMTPException("connect failed")

        with (
            mock.patch.object(
                CustomAccountAdapter.__mro__[1], "send_mail", side_effect=boom
            ),
            self.assertLogs("src.users.account_adapter", level="WARNING"),
            self.assertRaises(EmailDeliveryError),
        ):
            adapter.send_mail("account/email/password_reset_key", "x@y", {})

    def test_successful_send_passes_through(self):
        adapter = self._adapter()
        with mock.patch.object(
            CustomAccountAdapter.__mro__[1], "send_mail", return_value="sent"
        ) as super_send:
            result = adapter.send_mail("any/template", "x@y", {})
        self.assertEqual(result, "sent")
        super_send.assert_called_once()

    def test_non_smtp_errors_propagate(self):
        # A ValueError isn't an SMTP/network problem and must NOT be swallowed
        # as a 503 — keep the existing 500 behaviour so real bugs surface.
        adapter = self._adapter()
        with (
            mock.patch.object(
                CustomAccountAdapter.__mro__[1],
                "send_mail",
                side_effect=ValueError("bad template ctx"),
            ),
            self.assertRaises(ValueError),
        ):
            adapter.send_mail("any/template", "x@y", {})


class EmailDeliveryErrorMiddlewareTests(SimpleTestCase):
    """``process_exception`` must convert the error into a 503 response."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = EmailDeliveryErrorMiddleware(lambda req: HttpResponse(""))

    def test_renders_503_for_email_delivery_error(self):
        request = self.factory.post("/accounts/password/reset/")
        response = self.middleware.process_exception(
            request, EmailDeliveryError("Email service is temporarily unavailable.")
        )
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 503)
        body = response.content.decode("utf-8", errors="replace")
        # Either the rendered template or the inline fallback must mention the
        # status; the template uses "503" in its <h1>, and the fallback uses
        # "503 Service Unavailable".
        self.assertIn("503", body)

    def test_lets_other_exceptions_propagate(self):
        request = self.factory.get("/")
        self.assertIsNone(
            self.middleware.process_exception(request, RuntimeError("nope"))
        )


class EmailBackendSelectionTests(SimpleTestCase):
    """Guard the SENDGRID_API_KEY → SendGrid backend toggle.

    Prod runs on DigitalOcean which blocks outbound SMTP; the only reliable
    transport is the SendGrid HTTP API. The toggle must be unambiguous so
    that simply setting SENDGRID_API_KEY in the prod ``.env`` flips the
    project to API delivery without code changes.
    """

    def test_sendgrid_when_api_key_set(self):
        self.assertEqual(
            _default_email_backend(debug=False, sendgrid_api_key="SG.test"),
            "anymail.backends.sendgrid.EmailBackend",
        )

    def test_sendgrid_wins_even_in_debug(self):
        # Once a key is provisioned, we want it used everywhere — otherwise
        # local "works for me" testing would silently use a different backend
        # than prod.
        self.assertEqual(
            _default_email_backend(debug=True, sendgrid_api_key="SG.test"),
            "anymail.backends.sendgrid.EmailBackend",
        )

    def test_console_in_debug_without_sendgrid(self):
        self.assertEqual(
            _default_email_backend(debug=True, sendgrid_api_key=""),
            "django.core.mail.backends.console.EmailBackend",
        )

    def test_smtp_fallback_in_prod_without_sendgrid(self):
        # Preserves legacy SMTP behaviour as a fallback; in DO prod it will
        # 503 via CustomAccountAdapter, which is still better than a 500.
        self.assertEqual(
            _default_email_backend(debug=False, sendgrid_api_key=""),
            "django.core.mail.backends.smtp.EmailBackend",
        )

    def test_anymail_app_is_installed(self):
        # django-anymail must be on INSTALLED_APPS for its backend to load;
        # otherwise EmailBackend import would crash gunicorn boot. This
        # guards against a future "let's clean up unused apps" regression.
        self.assertIn("anymail", settings.INSTALLED_APPS)
