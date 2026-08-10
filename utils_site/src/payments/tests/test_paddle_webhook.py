"""Paddle webhook: normalisation, event routing and delivery handling."""

import hashlib
import hmac
import json
import time
from unittest import mock

from django.test import Client, TestCase, override_settings
from src.payments import handlers as h
from src.payments.paddle_webhook import EVENT_DISPATCH, _normalise
from src.users.models import WebhookEvent

SECRET = "pdl_ntfset_test_secret"
URL = "/payments/webhook/paddle/"


def _signed(body: bytes, secret: str = SECRET) -> str:
    ts = int(time.time())
    digest = hmac.new(
        secret.encode(), f"{ts}".encode() + b":" + body, hashlib.sha256
    ).hexdigest()
    return f"ts={ts};h1={digest}"


def _subscription_event(event_type="subscription.created", **overrides):
    data = {
        "id": "sub_01hv",
        "status": "active",
        "customer_id": "ctm_01hv",
        "custom_data": {"user_id": "7", "plan_id": "2", "locale": "pl"},
        "started_at": "2026-08-10T09:00:00Z",
        "current_billing_period": {
            "starts_at": "2026-08-10T09:00:00Z",
            "ends_at": "2026-09-10T09:00:00Z",
        },
    }
    data.update(overrides)
    return {"event_id": "evt_01", "event_type": event_type, "data": data}


class NormaliseTests(TestCase):
    def test_subscription_fields_land_where_handlers_look(self):
        out = _normalise("subscription.created", _subscription_event())
        self.assertEqual(out["_provider"], "paddle")
        # handlers.py reads custom_data from meta, not from data
        self.assertEqual(out["meta"]["custom_data"]["user_id"], "7")
        self.assertEqual(out["data"]["id"], "sub_01hv")
        attrs = out["data"]["attributes"]
        self.assertEqual(attrs["customer_id"], "ctm_01hv")
        self.assertEqual(attrs["renews_at"], "2026-09-10T09:00:00Z")

    def test_trialing_maps_to_the_vocabulary_handlers_speak(self):
        # handlers.py grants premium for "active"/"on_trial"; the raw Paddle
        # value "trialing" would silently fall through and leave a paying
        # trial user without access.
        out = _normalise("subscription.created", _subscription_event(status="trialing"))
        self.assertEqual(out["data"]["attributes"]["status"], "on_trial")

    def test_canceled_maps_to_cancelled(self):
        out = _normalise("subscription.updated", _subscription_event(status="canceled"))
        self.assertEqual(out["data"]["attributes"]["status"], "cancelled")

    def test_scheduled_cancellation_sets_period_end_flag(self):
        event = _subscription_event(
            "subscription.updated",
            scheduled_change={
                "action": "cancel",
                "effective_at": "2026-09-10T09:00:00Z",
            },
        )
        attrs = _normalise("subscription.updated", event)["data"]["attributes"]
        self.assertTrue(attrs["cancelled"])
        self.assertEqual(attrs["ends_at"], "2026-09-10T09:00:00Z")

    def test_no_scheduled_change_means_not_cancelled(self):
        attrs = _normalise("subscription.updated", _subscription_event())["data"][
            "attributes"
        ]
        self.assertNotIn("cancelled", attrs)

    def test_transaction_amount_converted_from_minor_unit_string(self):
        event = {
            "event_id": "evt_02",
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_01",
                "subscription_id": "sub_01hv",
                "customer_id": "ctm_01hv",
                "custom_data": {"user_id": "7", "plan_id": "2"},
                "details": {"totals": {"grand_total": "799", "currency_code": "USD"}},
            },
        }
        attrs = _normalise("transaction.completed", event)["data"]["attributes"]
        # handlers.py does Decimal(total) / 100 -> 7.99
        self.assertEqual(attrs["total"], 799)
        self.assertEqual(attrs["order_id"], "txn_01")
        self.assertEqual(attrs["subscription_id"], "sub_01hv")

    def test_missing_total_does_not_explode(self):
        event = {"event_id": "e", "event_type": "transaction.completed", "data": {}}
        attrs = _normalise("transaction.completed", event)["data"]["attributes"]
        self.assertEqual(attrs["total"], 0)


class EventRoutingTests(TestCase):
    def test_canceled_revokes_access_rather_than_only_flagging_it(self):
        # Paddle fires subscription.canceled when cancellation takes EFFECT.
        # Routing it to handle_subscription_cancelled (the Lemon Squeezy
        # meaning: "scheduled, keep premium until period end") would leave
        # premium enabled forever, because nothing else revokes it.
        self.assertIs(
            EVENT_DISPATCH["subscription.canceled"], h.handle_subscription_expired
        )
        self.assertIsNot(
            EVENT_DISPATCH["subscription.canceled"], h.handle_subscription_cancelled
        )


@override_settings(PADDLE_WEBHOOK_SECRET=SECRET)
class WebhookDeliveryTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _post(self, payload, signature=None):
        body = json.dumps(payload).encode()
        return self.client.post(
            URL,
            data=body,
            content_type="application/json",
            headers={"paddle-signature": signature or _signed(body)},
        )

    def test_rejects_bad_signature_without_running_handler(self):
        with mock.patch.object(h, "handle_subscription_created") as handler:
            r = self._post(_subscription_event(), signature="ts=1;h1=deadbeef")
        self.assertEqual(r.status_code, 400)
        handler.assert_not_called()
        self.assertFalse(WebhookEvent.objects.exists())

    def test_duplicate_delivery_runs_handler_once(self):
        payload = _subscription_event()
        with mock.patch(
            "src.payments.paddle_webhook.EVENT_DISPATCH",
            {"subscription.created": mock.Mock()},
        ) as dispatch:
            handler = dispatch["subscription.created"]
            self.assertEqual(self._post(payload).status_code, 200)
            self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(handler.call_count, 1)
        self.assertEqual(WebhookEvent.objects.filter(provider="paddle").count(), 1)

    def test_stores_the_original_payload_not_the_normalised_one(self):
        payload = _subscription_event()
        with mock.patch(
            "src.payments.paddle_webhook.EVENT_DISPATCH",
            {"subscription.created": mock.Mock()},
        ):
            self._post(payload)
        evt = WebhookEvent.objects.get(provider="paddle")
        self.assertEqual(evt.raw_payload["data"]["status"], "active")
        self.assertNotIn("_provider", evt.raw_payload)

    def test_unhandled_event_is_acknowledged(self):
        r = self._post({"event_id": "e9", "event_type": "report.created", "data": {}})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(WebhookEvent.objects.exists())

    @override_settings(PADDLE_WEBHOOK_SECRET="")
    def test_unconfigured_secret_returns_503(self):
        r = self._post(_subscription_event())
        self.assertEqual(r.status_code, 503)
