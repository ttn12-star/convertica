import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal

from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from src.payments.tests.fixtures.ls_payloads import (
    order_created_payload,
    subscription_created_payload,
)
from src.users.models import SubscriptionPlan, User, UserSubscription, WebhookEvent

SECRET = "test-webhook-secret-32chars-or-more"


def signed_post(client, url, payload, secret=SECRET):
    body = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        url,
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
        HTTP_X_EVENT_NAME=payload["meta"]["event_name"],
    )


@override_settings(LEMONSQUEEZY_WEBHOOK_SECRET=SECRET)
class WebhookViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="w@t.test", password="x")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="var_1",
        )
        self.url = reverse("ls_webhook")
        self.client = Client()

    def test_rejects_missing_signature(self):
        body = json.dumps({"x": 1}).encode()
        r = self.client.post(self.url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_rejects_wrong_signature(self):
        body = json.dumps({"meta": {"event_name": "x"}}).encode()
        r = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE="deadbeef",
        )
        self.assertEqual(r.status_code, 400)

    def test_rejects_when_secret_unconfigured(self):
        with override_settings(LEMONSQUEEZY_WEBHOOK_SECRET=""):
            body = json.dumps({"x": 1}).encode()
            r = self.client.post(
                self.url,
                data=body,
                content_type="application/json",
                HTTP_X_SIGNATURE="anything",
            )
            self.assertEqual(r.status_code, 503)

    def test_dispatches_subscription_created(self):
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.plan.id,
        )
        r = signed_post(self.client, self.url, payload)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())
        self.assertTrue(WebhookEvent.objects.filter(provider="lemonsqueezy").exists())

    def test_idempotent_on_duplicate_event(self):
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.plan.id,
        )
        signed_post(self.client, self.url, payload)
        signed_post(self.client, self.url, payload)
        # Both calls succeed, but only one UserSubscription, one WebhookEvent.
        self.assertEqual(UserSubscription.objects.filter(user=self.user).count(), 1)
        self.assertEqual(WebhookEvent.objects.count(), 1)

    def _event_row_for(self, payload, **overrides):
        """Create the WebhookEvent row the view would have for this payload."""
        from src.payments.webhook import _build_event_id

        event_id = _build_event_id(payload, RequestFactory().post(self.url))
        fields = {
            "provider": "lemonsqueezy",
            "event_id": event_id,
            "event_type": payload["meta"]["event_name"],
            "raw_payload": payload,
        }
        fields.update(overrides)
        return WebhookEvent.objects.create(**fields)

    def test_stale_processing_event_is_reclaimed(self):
        """A worker killed mid-handler (OOM/SIGKILL) leaves processing=True
        forever; the LS retry must be able to reclaim and finish the event."""
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.plan.id,
        )
        evt = self._event_row_for(payload, processing=True)
        WebhookEvent.objects.filter(pk=evt.pk).update(
            updated_at=timezone.now() - timedelta(minutes=30)
        )

        r = signed_post(self.client, self.url, payload)

        self.assertEqual(r.status_code, 200)
        evt.refresh_from_db()
        self.assertIsNotNone(evt.processed_at)
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())

    def test_fresh_processing_event_is_not_double_processed(self):
        """While another worker is actively on the event, skip — LS retries."""
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.plan.id,
        )
        evt = self._event_row_for(payload, processing=True)

        r = signed_post(self.client, self.url, payload)

        self.assertEqual(r.status_code, 200)
        evt.refresh_from_db()
        self.assertIsNone(evt.processed_at)
        self.assertFalse(UserSubscription.objects.filter(user=self.user).exists())

    def test_handles_order_created_lifetime(self):
        lifetime = SubscriptionPlan.objects.create(
            name="Lifetime",
            slug="lifetime",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            ls_variant_id="var_lifetime",
        )
        payload = order_created_payload(
            user_id=self.user.id,
            plan_id=lifetime.id,
        )
        r = signed_post(self.client, self.url, payload)
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(self.user.subscription_end_date)
