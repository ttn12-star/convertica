"""Regression tests for the account-email delivery path.

Covers the case that flooded Sentry as CONVERTICA-50/51 in May 2026:
the prod container briefly couldn't reach the SMTP host, every
allauth email-sending view (signup, password reset, resend-confirmation)
500'd for live users.

The protection is now layered like this:

1. ``CustomAccountAdapter.send_mail`` renders the message in-request
   (template bugs still surface as 500s) and queues the
   ``email.send_account_email`` Celery task — ESP latency/outages no
   longer block the gunicorn worker, and transient failures are retried
   in the background.
2. If handing off to the broker fails — or, under eager mode (dev,
   tests), the inline send hits an SMTP/ESP error — the adapter
   translates it into the controlled ``EmailDeliveryError``.
3. ``EmailDeliveryErrorMiddleware`` catches that exception in
   ``process_exception`` and renders a 503 instead of a 500.
"""

from __future__ import annotations

import smtplib
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from src.tasks.email import send_account_email
from src.users.account_adapter import CustomAccountAdapter, EmailDeliveryError
from src.users.middleware import EmailDeliveryErrorMiddleware

from utils_site.settings import _default_email_backend


def _rendered_message() -> EmailMultiAlternatives:
    msg = EmailMultiAlternatives(
        subject="Confirm your email",
        body="plain body",
        from_email="noreply@convertica.net",
        to=["x@y"],
    )
    msg.attach_alternative("<p>html body</p>", "text/html")
    return msg


@override_settings(EMAIL_HOST="smtp.example.test", EMAIL_PORT=587)
class CustomAccountAdapterSendMailTests(SimpleTestCase):
    """``send_mail`` must queue the rendered message and translate
    infrastructure failures into ``EmailDeliveryError``."""

    def _adapter(self):
        return CustomAccountAdapter()

    def test_renders_in_request_and_queues_task(self):
        adapter = self._adapter()
        with (
            mock.patch.object(
                CustomAccountAdapter, "render_mail", return_value=_rendered_message()
            ) as render,
            mock.patch("src.users.account_adapter.send_account_email") as task,
        ):
            adapter.send_mail("account/email/email_confirmation", "x@y", {})

        render.assert_called_once()
        task.delay.assert_called_once_with(
            subject="Confirm your email",
            body="plain body",
            from_email="noreply@convertica.net",
            to=["x@y"],
            html_body="<p>html body</p>",
        )

    def test_broker_failure_is_translated(self):
        # Redis down → .delay() raises kombu OperationalError; the user must
        # get the controlled 503, not a 500 white page.
        from kombu.exceptions import OperationalError

        adapter = self._adapter()
        boom = OperationalError("Connection refused")
        with (
            mock.patch.object(
                CustomAccountAdapter, "render_mail", return_value=_rendered_message()
            ),
            mock.patch("src.users.account_adapter.send_account_email") as task,
            self.assertLogs("src.users.account_adapter", level="WARNING") as captured,
            self.assertRaises(EmailDeliveryError) as exc_ctx,
        ):
            task.delay.side_effect = boom
            adapter.send_mail("account/email/email_confirmation", "x@y", {})

        # __cause__ preserved for traceability in Sentry.
        self.assertIs(exc_ctx.exception.__cause__, boom)
        # Warning must include enough context to debug the outage.
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertIn("Email delivery failed", record.getMessage())
        self.assertEqual(record.event, "email_delivery_failed")
        self.assertEqual(record.email_host, "smtp.example.test")
        self.assertEqual(record.email_port, 587)

    def test_eager_smtp_exception_is_translated(self):
        # Under CELERY_TASK_ALWAYS_EAGER (dev/console, integration tests) the
        # task runs inline and SMTP errors propagate out of .delay() — the
        # CONVERTICA-50/51 translation must still apply.
        adapter = self._adapter()
        with (
            mock.patch.object(
                CustomAccountAdapter, "render_mail", return_value=_rendered_message()
            ),
            mock.patch("src.users.account_adapter.send_account_email") as task,
            self.assertLogs("src.users.account_adapter", level="WARNING"),
            self.assertRaises(EmailDeliveryError),
        ):
            task.delay.side_effect = smtplib.SMTPException("connect failed")
            adapter.send_mail("account/email/password_reset_key", "x@y", {})

    def test_eager_anymail_error_is_translated(self):
        # When SendGrid/Brevo (anymail-backed ESP) returns 4xx/5xx inline, the
        # backend raises AnymailRequestsAPIError, which is *not* an OSError
        # and *not* an SMTPException. Without this catch, signup/password
        # reset would fall back to 500 white pages under eager mode.
        from anymail.exceptions import AnymailRequestsAPIError

        adapter = self._adapter()
        boom = AnymailRequestsAPIError(
            "SendGrid API response 401 (Unauthorized): Maximum credits exceeded",
        )
        with (
            mock.patch.object(
                CustomAccountAdapter, "render_mail", return_value=_rendered_message()
            ),
            mock.patch("src.users.account_adapter.send_account_email") as task,
            self.assertLogs("src.users.account_adapter", level="WARNING"),
            self.assertRaises(EmailDeliveryError),
        ):
            task.delay.side_effect = boom
            adapter.send_mail("account/email/email_confirmation", "x@y", {})

    def test_render_errors_propagate(self):
        # A template/context bug isn't an infrastructure problem and must NOT
        # be swallowed as a 503 — keep the 500 behaviour so real bugs surface.
        adapter = self._adapter()
        with (
            mock.patch.object(
                CustomAccountAdapter,
                "render_mail",
                side_effect=ValueError("bad template ctx"),
            ),
            self.assertRaises(ValueError),
        ):
            adapter.send_mail("any/template", "x@y", {})


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SendAccountEmailTaskTests(SimpleTestCase):
    """The Celery task must deliver the pre-rendered message."""

    def test_sends_rendered_message_with_html_alternative(self):
        send_account_email.delay(
            subject="Confirm your email",
            body="plain body",
            from_email="noreply@convertica.net",
            to=["x@y"],
            html_body="<p>html body</p>",
        )

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, "Confirm your email")
        self.assertEqual(sent.to, ["x@y"])
        self.assertEqual(sent.alternatives, [("<p>html body</p>", "text/html")])

    def test_eager_delivery_error_propagates_without_retry(self):
        # Inline (eager) execution must not loop through retries — the
        # adapter translates the propagated error into the 503 path instead.
        with (
            mock.patch.object(
                EmailMultiAlternatives,
                "send",
                side_effect=smtplib.SMTPException("connect failed"),
            ) as send,
            self.assertRaises(smtplib.SMTPException),
        ):
            send_account_email.delay(
                subject="s",
                body="b",
                from_email="noreply@convertica.net",
                to=["x@y"],
            )
        self.assertEqual(send.call_count, 1)


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
    """Guard the BREVO_API_KEY → Brevo backend toggle.

    Prod runs on DigitalOcean which blocks outbound SMTP; the only reliable
    transport is Brevo's HTTP API. The toggle must be unambiguous so that
    simply setting BREVO_API_KEY in the prod ``.env`` flips the project to
    API delivery without code changes.
    """

    def test_brevo_when_api_key_set(self):
        self.assertEqual(
            _default_email_backend(debug=False, brevo_api_key="xkeysib-test"),
            "anymail.backends.brevo.EmailBackend",
        )

    def test_brevo_wins_even_in_debug(self):
        # Once a key is provisioned, we want it used everywhere — otherwise
        # local "works for me" testing would silently use a different backend
        # than prod.
        self.assertEqual(
            _default_email_backend(debug=True, brevo_api_key="xkeysib-test"),
            "anymail.backends.brevo.EmailBackend",
        )

    def test_console_in_debug_without_brevo(self):
        self.assertEqual(
            _default_email_backend(debug=True, brevo_api_key=""),
            "django.core.mail.backends.console.EmailBackend",
        )

    def test_smtp_fallback_in_prod_without_brevo(self):
        # Preserves legacy SMTP behaviour as a fallback; in DO prod it will
        # 503 via CustomAccountAdapter, which is still better than a 500.
        self.assertEqual(
            _default_email_backend(debug=False, brevo_api_key=""),
            "django.core.mail.backends.smtp.EmailBackend",
        )

    def test_anymail_app_is_installed(self):
        # django-anymail must be on INSTALLED_APPS for its backend to load;
        # otherwise EmailBackend import would crash gunicorn boot. This
        # guards against a future "let's clean up unused apps" regression.
        self.assertIn("anymail", settings.INSTALLED_APPS)
