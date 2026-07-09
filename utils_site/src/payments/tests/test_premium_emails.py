"""Premium welcome / renewal email triggers + localized rendering."""

from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.utils import translation
from src.payments import handlers
from src.payments.handlers import (
    _resolve_email_lang,
    handle_order_created,
    handle_subscription_created,
    handle_subscription_payment_success,
)
from src.payments.tests.fixtures.ls_payloads import (
    order_created_payload,
    subscription_created_payload,
    subscription_payment_success_payload,
)
from src.tasks.email import send_premium_email
from src.users.models import SubscriptionPlan, User


class TriggerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buyer@t.test", password="x")
        self.monthly = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="var_1",
        )
        self.lifetime = SubscriptionPlan.objects.create(
            name="Lifetime",
            slug="lifetime",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            ls_variant_id="var_lifetime",
        )

    def _kinds(self, mock_task):
        # positional args are (user_id, kind, lang)
        return [call.args[1] for call in mock_task.delay.call_args_list]


class WelcomeTriggerTests(TriggerTestCase):
    def test_welcome_sent_once_and_only_once(self):
        payload = subscription_created_payload(
            user_id=self.user.id, plan_id=self.monthly.id
        )
        with (
            patch.object(handlers, "send_premium_email") as task,
            self.captureOnCommitCallbacks(execute=True),
        ):
            handle_subscription_created(payload)
            # Redelivery of the same event (bypassing the webhook dedup)
            # must not send a second welcome.
            handle_subscription_created(payload)

        self.assertEqual(self._kinds(task), ["welcome"])
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.welcome_email_sent_at)

    def test_lifetime_order_sends_welcome(self):
        payload = order_created_payload(user_id=self.user.id, plan_id=self.lifetime.id)
        with (
            patch.object(handlers, "send_premium_email") as task,
            self.captureOnCommitCallbacks(execute=True),
        ):
            handle_order_created(payload)
        self.assertEqual(self._kinds(task), ["welcome"])


class RenewalTriggerTests(TriggerTestCase):
    def test_first_payment_no_renewal_second_payment_renews(self):
        with (
            patch.object(handlers, "send_premium_email") as task,
            self.captureOnCommitCallbacks(execute=True),
        ):
            handle_subscription_created(
                subscription_created_payload(
                    user_id=self.user.id, plan_id=self.monthly.id
                )
            )
            # First charge — no prior completed payment → not a renewal.
            handle_subscription_payment_success(
                subscription_payment_success_payload(
                    user_id=self.user.id,
                    plan_id=self.monthly.id,
                    order_id="ord_1",
                )
            )
            # Second cycle — a completed payment already exists → renewal.
            handle_subscription_payment_success(
                subscription_payment_success_payload(
                    user_id=self.user.id,
                    plan_id=self.monthly.id,
                    order_id="ord_2",
                )
            )

        self.assertEqual(self._kinds(task), ["welcome", "renewal"])


class LangResolutionTests(TriggerTestCase):
    def test_custom_data_locale_wins(self):
        self.user.preferred_language = "es"
        payload = subscription_created_payload(
            user_id=self.user.id, plan_id=self.monthly.id
        )
        payload["meta"]["custom_data"]["locale"] = "ru"
        self.assertEqual(_resolve_email_lang(payload, self.user), "ru")

    def test_falls_back_to_preferred_language(self):
        self.user.preferred_language = "pl"
        payload = subscription_created_payload(
            user_id=self.user.id, plan_id=self.monthly.id
        )
        self.assertEqual(_resolve_email_lang(payload, self.user), "pl")

    def test_unsupported_locale_falls_back_to_default(self):
        self.user.preferred_language = ""
        payload = subscription_created_payload(
            user_id=self.user.id, plan_id=self.monthly.id
        )
        payload["meta"]["custom_data"]["locale"] = "zz"
        self.assertEqual(_resolve_email_lang(payload, self.user), "en")


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RenderTests(TriggerTestCase):
    def test_renders_localized_subject_and_body(self):
        self.user.first_name = "Иван"
        self.user.save(update_fields=["first_name"])
        mail.outbox = []
        send_premium_email.apply(args=[self.user.id, "renewal", "ru"]).get()
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "Спасибо за продление Convertica Premium")
        self.assertIn("Здравствуйте, Иван!", msg.body)
        # Support address is configurable (CONTACT_EMAIL); assert the actual value.
        support = getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)
        self.assertIn(support, msg.body)
        # Subject line must not leak into the body.
        self.assertNotIn("Convertica Premium\n\n", msg.subject)
        # Multipart: a branded HTML alternative rides along with the text part.
        self.assertTrue(msg.alternatives, "email should be multipart with HTML")
        html, mime = msg.alternatives[0]
        self.assertEqual(mime, "text/html")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Здравствуйте, Иван!", html)

    def test_neutral_greeting_when_no_name(self):
        mail.outbox = []
        send_premium_email.apply(args=[self.user.id, "welcome", "en"]).get()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hi there,", mail.outbox[0].body)


class AllTemplatesRenderTests(TestCase):
    """Guard every shipped language file: no syntax error, no leaked tags."""

    CTX = {
        "greeting_name": "Sam",
        "site_url": "https://convertica.net",
        "profile_url": "https://convertica.net/users/profile/",
        "support_email": "info@convertica.net",
    }

    def test_every_kind_and_language_renders(self):
        for kind in ("welcome", "renewal"):
            for code, _label in settings.LANGUAGES:
                with self.subTest(kind=kind, lang=code):
                    ctx = {**self.CTX, "email_lang": code, "rtl": code == "ar"}
                    with translation.override(code):
                        txt = render_to_string(f"emails/premium/{kind}_{code}.txt", ctx)
                        html = render_to_string(
                            f"emails/premium/{kind}_{code}.html", ctx
                        )
                    subject, _sep, body = txt.partition("\n")
                    self.assertTrue(subject.strip(), "subject must be non-empty")
                    self.assertTrue(body.strip(), "body must be non-empty")
                    for out in (txt, html):
                        # No unrendered Django tags/variables leaked through.
                        self.assertNotIn("{{", out)
                        self.assertNotIn("{%", out)
                        # Personalized greeting resolved to the name branch.
                        self.assertIn("Sam", out)
                        self.assertIn("https://convertica.net", out)
                    self.assertIn("<!DOCTYPE html>", html)


class LanguagePersistenceFlowTests(TestCase):
    """End-to-end: explicit switch persists; login restores it on a new device."""

    def setUp(self):
        from allauth.account.models import EmailAddress

        self.user = User.objects.create_user(email="lang@t.test", password="pw12345!")
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, primary=True, verified=True
        )

    def test_switch_persists_and_login_restores_cookie(self):
        from django.urls import reverse

        self.client.force_login(self.user)
        self.client.post("/i18n/setlang/", {"language": "ru", "next": "/"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "ru")

        # Fresh client == fresh device: no language cookie yet. Post to the
        # locale-prefixed login URL (the form's {% url %} action) so the view
        # runs instead of getting bounced by the i18n redirect.
        self.client.logout()
        fresh = self.client.__class__()
        resp = fresh.post(
            reverse("users:login"),
            {"email": "lang@t.test", "password": "pw12345!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "ru")
