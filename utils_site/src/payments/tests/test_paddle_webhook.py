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


@override_settings(PADDLE_WEBHOOK_SECRET=SECRET)
class EndToEndPremiumTests(TestCase):
    """A signed Paddle delivery must actually grant and revoke premium.

    The unit tests above check normalisation and routing separately; this one
    catches the case where both are individually right but disagree — e.g. a
    field renamed on one side only, which would silently leave a paying
    customer without access.
    """

    def setUp(self):
        from src.users.models import SubscriptionPlan, User

        self.user = User.objects.create_user(
            username="payer", email="payer@example.com", password="x"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly-test",
            price="7.99",
            currency="USD",
            duration_days=30,
        )
        self.client = Client()

    def _deliver(self, payload):
        body = json.dumps(payload).encode()
        return self.client.post(
            URL,
            data=body,
            content_type="application/json",
            headers={"paddle-signature": _signed(body)},
        )

    def _event(self, event_type, event_id, **data_overrides):
        data = {
            "id": "sub_e2e",
            "status": "active",
            "customer_id": "ctm_e2e",
            "custom_data": {
                "user_id": str(self.user.id),
                "plan_id": str(self.plan.id),
                "locale": "en",
            },
            "started_at": "2026-08-10T09:00:00Z",
            "current_billing_period": {
                "starts_at": "2026-08-10T09:00:00Z",
                "ends_at": "2026-09-10T09:00:00Z",
            },
        }
        data.update(data_overrides)
        return {"event_id": event_id, "event_type": event_type, "data": data}

    def test_subscription_created_grants_premium(self):
        r = self._deliver(self._event("subscription.created", "evt_e2e_1"))
        self.assertEqual(r.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertTrue(self.user.is_subscription_active())

        sub = self.user.provider_subscription
        self.assertEqual(sub.provider, "paddle")  # not "lemonsqueezy"
        self.assertEqual(sub.provider_subscription_id, "sub_e2e")
        self.assertEqual(sub.provider_customer_id, "ctm_e2e")

    def test_cancellation_taking_effect_revokes_premium(self):
        self._deliver(self._event("subscription.created", "evt_e2e_2"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

        r = self._deliver(
            self._event("subscription.canceled", "evt_e2e_3", status="canceled")
        )
        self.assertEqual(r.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscription_active())

    def test_completed_transaction_records_the_payment(self):
        from decimal import Decimal

        from src.users.models import Payment

        self._deliver(self._event("subscription.created", "evt_e2e_4"))
        txn = {
            "event_id": "evt_e2e_5",
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_e2e",
                "subscription_id": "sub_e2e",
                "customer_id": "ctm_e2e",
                "custom_data": {
                    "user_id": str(self.user.id),
                    "plan_id": str(self.plan.id),
                },
                "details": {"totals": {"grand_total": "799", "currency_code": "USD"}},
            },
        }
        self.assertEqual(self._deliver(txn).status_code, 200)

        payment = Payment.objects.get(user=self.user, status="completed")
        # Minor units must become 7.99, not 799.
        self.assertEqual(payment.amount, Decimal("7.99"))
        self.assertEqual(payment.provider, "paddle")


@override_settings(PADDLE_WEBHOOK_SECRET=SECRET)
class BrokerOutageTests(TestCase):
    """A dead Celery broker must not cost the customer their premium.

    The email is queued from an on_commit hook, so by the time it fails the
    subscription is already committed. Letting the exception escape makes the
    webhook return 500, Paddle retry an already-successful delivery, and the
    welcome mail never send (its claim is committed too).
    """

    def setUp(self):
        from src.users.models import SubscriptionPlan, User

        self.user = User.objects.create_user(
            username="broker", email="broker@example.com", password="x"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly-broker",
            price="7.99",
            currency="USD",
            duration_days=30,
        )

    def test_premium_survives_a_dead_broker(self):
        payload = {
            "event_id": "evt_broker",
            "event_type": "subscription.created",
            "data": {
                "id": "sub_broker",
                "status": "active",
                "customer_id": "ctm_broker",
                "custom_data": {
                    "user_id": str(self.user.id),
                    "plan_id": str(self.plan.id),
                    "locale": "en",
                },
                "started_at": "2026-08-10T09:00:00Z",
                "current_billing_period": {
                    "starts_at": "2026-08-10T09:00:00Z",
                    "ends_at": "2026-09-10T09:00:00Z",
                },
            },
        }
        body = json.dumps(payload).encode()
        with mock.patch(
            "src.payments.handlers.send_premium_email.delay",
            side_effect=RuntimeError("Retry limit exceeded while trying to reconnect"),
        ):
            r = Client().post(
                URL,
                data=body,
                content_type="application/json",
                headers={"paddle-signature": _signed(body)},
            )

        self.assertEqual(r.status_code, 200)  # not 500 — no pointless retries
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        evt = WebhookEvent.objects.get(event_id="evt_broker")
        self.assertIsNotNone(evt.processed_at)
