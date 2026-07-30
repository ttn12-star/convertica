"""Branded allauth account emails: signup confirmation and password reset.

Guards the bug these templates were written for: the prod Site row has an empty
name/domain, so allauth's defaults sent "Hello from !", "register an account
on ." and the subject "[] Please Confirm Your Email Address".
"""

import pathlib
import re

from allauth.core import context
from django.conf import settings
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.utils import translation
from src.users.account_adapter import CustomAccountAdapter

CONFIRM_URL = "https://convertica.net/accounts/confirm-email/KEY-123/"
RESET_URL = "https://convertica.net/accounts/password/reset/key/7-abc/"
LOCALES = [code for code, _label in settings.LANGUAGES]


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountEmailRenderTests(TestCase):
    def _send(self, prefix, ctx, lang="en"):
        user = type("U", (), {"first_name": "Nikita", "username": "nikita"})()
        # allauth renders with the request, so the site's context processors run
        # too — keep the default "testserver" host, which the test runner allows
        # (a real domain here needs ALLOWED_HOSTS and fails on CI).
        request = RequestFactory().get("/")
        with translation.override(lang), context.request_context(request):
            CustomAccountAdapter().send_mail(prefix, "x@y.com", {**ctx, "user": user})
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        html = sent.alternatives[0][0]
        return sent, html

    def test_signup_confirmation_is_branded_html_and_text(self):
        sent, html = self._send(
            "account/email/email_confirmation_signup", {"activate_url": CONFIRM_URL}
        )

        self.assertEqual(sent.subject, "Confirm your email to finish signing up")
        # Bare "noreply@..." in the From line looks like spam.
        self.assertTrue(sent.from_email.startswith("Convertica <"), sent.from_email)
        for body in (sent.body, html):
            self.assertIn("Convertica", body)
            self.assertIn(CONFIRM_URL, body)
            # The empty-Site symptoms: "from !", "on .", "using !".
            self.assertNotRegex(body, r"(from|on|using) [!.]")
        self.assertIn("Hi Nikita,", html)
        self.assertIn("Confirm my email", html)

    def test_password_reset_is_branded(self):
        sent, html = self._send(
            "account/email/password_reset_key", {"password_reset_url": RESET_URL}
        )

        self.assertEqual(sent.subject, "Reset your Convertica password")
        self.assertIn(RESET_URL, sent.body)
        self.assertIn(RESET_URL, html)
        self.assertIn("Set a new password", html)

    def test_email_address_username_is_not_used_as_a_greeting(self):
        user = type("U", (), {"first_name": "", "username": "bob@example.com"})()
        self.assertEqual(
            CustomAccountAdapter()._brand_context({"user": user})["greeting_name"], ""
        )

    def test_arabic_renders_rtl(self):
        _sent, html = self._send(
            "account/email/email_confirmation_signup",
            {"activate_url": CONFIRM_URL},
            lang="ar",
        )
        self.assertIn('dir="rtl"', html)
        self.assertIn("text-align:right", html)


class AccountEmailTranslationTests(TestCase):
    """Every locale must carry the new strings.

    Asserted against the .po sources, not a rendered template: the CI test job
    does not run compilemessages, so a render-based check passes locally on
    stale .mo files and fails the deploy gate.
    """

    def test_all_locales_translate_the_account_email_strings(self):
        markers = [
            "Confirm my email",
            "Confirm your email to finish signing up",
            "Set a new password",
            "Hi %(greeting_name)s,",
        ]
        root = pathlib.Path(settings.BASE_DIR) / "locale"
        for lang in LOCALES:
            po = (root / lang / "LC_MESSAGES/django.po").read_text()
            for marker in markers:
                match = re.search(
                    rf'^msgid "{re.escape(marker)}"\nmsgstr "(.*)"$', po, re.M
                )
                self.assertIsNotNone(match, f"{lang}: missing msgid {marker!r}")
                self.assertTrue(match.group(1), f"{lang}: empty msgstr for {marker!r}")
                if "%(greeting_name)s" in marker:
                    self.assertIn("%(greeting_name)s", match.group(1), lang)
