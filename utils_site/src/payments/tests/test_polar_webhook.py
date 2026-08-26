"""Polar webhook: signature scheme, normalisation, routing and delivery."""

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

from django.test import Client, TestCase, override_settings
from src.payments import handlers as h
from src.payments.polar_webhook import EVENT_DISPATCH, _normalise
from src.payments.webhook_security import verify_polar_signature
from src.users.models import Payment, SubscriptionPlan, User, WebhookEvent

# Standard Webhooks treats the secret as base64, so the test secret has to be
# valid base64 or both sides would silently derive different keys.
SECRET = base64.b64encode(b"polar-test-secret-key-32-bytes!!").decode()
URL = "/payments/webhook/polar/"


def _headers(body: bytes, secret: str = SECRET, msg_id="msg_1", ts=None) -> dict:
    """Sign `body` the way Polar does: HMAC over `<id>.<ts>.<body>`."""
    ts = int(time.time()) if ts is None else ts
    key = base64.b64decode(secret + "==")
    sig = hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()
    return {
        "webhook-id": msg_id,
        "webhook-timestamp": str(ts),
        "webhook-signature": "v1," + base64.b64encode(sig).decode(),
    }


def _subscription(**overrides) -> dict:
    data = {
        "id": "sub_polar_1",
        "status": "active",
        "customer_id": "cus_polar_1",
        "product_id": "prod_polar_1",
        "started_at": "2026-08-26T09:00:00Z",
        "current_period_start": "2026-08-26T09:00:00Z",
        "current_period_end": "2026-09-26T09:00:00Z",
        "cancel_at_period_end": False,
        "ends_at": None,
        "metadata": {"user_id": "7", "plan_id": "2", "locale": "pl"},
        "customer": {"id": "cus_polar_1", "external_id": "7", "metadata": {}},
    }
    data.update(overrides)
    return data


def _event(event_type: str, data: dict) -> dict:
    return {"type": event_type, "timestamp": "2026-08-26T09:00:00Z", "data": data}


class SignatureTests(TestCase):
    def test_accepts_a_correctly_signed_delivery(self):
        body = b'{"type":"subscription.created"}'
        self.assertTrue(verify_polar_signature(body, _headers(body), SECRET))

    def test_rejects_a_tampered_body(self):
        body = b'{"type":"subscription.created"}'
        headers = _headers(body)
        self.assertFalse(
            verify_polar_signature(body + b" ", headers, SECRET),
            "a body edited in flight must not verify",
        )

    def test_rejects_a_swapped_message_id(self):
        # The id is inside the signed string, so it cannot be changed on its own.
        body = b"{}"
        headers = _headers(body, msg_id="msg_1")
        headers["webhook-id"] = "msg_2"
        self.assertFalse(verify_polar_signature(body, headers, SECRET))

    def test_rejects_a_replay_outside_the_window(self):
        body = b"{}"
        stale = int(time.time()) - 6 * 60
        self.assertFalse(verify_polar_signature(body, _headers(body, ts=stale), SECRET))

    def test_rejects_a_timestamp_from_the_future(self):
        body = b"{}"
        ahead = int(time.time()) + 6 * 60
        self.assertFalse(verify_polar_signature(body, _headers(body, ts=ahead), SECRET))

    def test_whsec_prefix_is_stripped_before_decoding(self):
        body = b"{}"
        # Polar-generated secrets carry the prefix; ours do not. Both must work,
        # and both must derive the SAME key or a rotation would break delivery.
        self.assertTrue(
            verify_polar_signature(body, _headers(body, SECRET), "whsec_" + SECRET)
        )

    def test_missing_headers_are_rejected(self):
        self.assertFalse(verify_polar_signature(b"{}", {}, SECRET))

    def test_accepts_when_one_of_several_signatures_matches(self):
        # Polar sends a space-separated list during a secret rotation.
        body = b"{}"
        headers = _headers(body)
        headers["webhook-signature"] = "v1,AAAA " + headers["webhook-signature"]
        self.assertTrue(verify_polar_signature(body, headers, SECRET))


class NormaliseTests(TestCase):
    def test_subscription_fields_land_where_handlers_look(self):
        out = _normalise("subscription.created", _event("x", _subscription()))
        self.assertEqual(out["_provider"], "polar")
        self.assertEqual(out["meta"]["custom_data"]["user_id"], "7")
        self.assertEqual(out["meta"]["custom_data"]["plan_id"], "2")
        self.assertEqual(out["data"]["id"], "sub_polar_1")
        attrs = out["data"]["attributes"]
        self.assertEqual(attrs["customer_id"], "cus_polar_1")
        self.assertEqual(attrs["created_at"], "2026-08-26T09:00:00Z")
        self.assertEqual(attrs["renews_at"], "2026-09-26T09:00:00Z")

    def test_subscription_id_is_present_on_subscription_events(self):
        # handle_subscription_payment_failed reads attrs["subscription_id"],
        # not data["id"] — without this, past_due would update no row at all.
        attrs = _normalise("subscription.past_due", _event("x", _subscription()))[
            "data"
        ]["attributes"]
        self.assertEqual(attrs["subscription_id"], "sub_polar_1")

    def test_trialing_maps_to_the_vocabulary_handlers_speak(self):
        attrs = _normalise(
            "subscription.created", _event("x", _subscription(status="trialing"))
        )["data"]["attributes"]
        self.assertEqual(attrs["status"], "on_trial")

    def test_canceled_maps_to_cancelled(self):
        attrs = _normalise(
            "subscription.updated", _event("x", _subscription(status="canceled"))
        )["data"]["attributes"]
        self.assertEqual(attrs["status"], "cancelled")

    def test_incomplete_does_not_read_as_active(self):
        # `incomplete` means the first payment has not landed. Passing it
        # through unmapped would leave handlers with an unknown status; mapping
        # it to "active" would hand out premium for free.
        attrs = _normalise(
            "subscription.created", _event("x", _subscription(status="incomplete"))
        )["data"]["attributes"]
        self.assertEqual(attrs["status"], "unpaid")

    def test_scheduled_cancellation_sets_the_period_end_flag(self):
        data = _subscription(cancel_at_period_end=True, ends_at="2026-09-26T09:00:00Z")
        attrs = _normalise("subscription.canceled", _event("x", data))["data"][
            "attributes"
        ]
        self.assertTrue(attrs["cancelled"])
        self.assertEqual(attrs["ends_at"], "2026-09-26T09:00:00Z")

    def test_not_cancelled_leaves_the_flag_off(self):
        attrs = _normalise("subscription.updated", _event("x", _subscription()))[
            "data"
        ]["attributes"]
        self.assertNotIn("cancelled", attrs)

    def test_order_total_is_what_the_customer_paid(self):
        order = {
            "id": "ord_1",
            "status": "paid",
            "customer_id": "cus_polar_1",
            "product_id": "prod_polar_1",
            "subscription_id": "sub_polar_1",
            "subtotal_amount": 799,
            "tax_amount": 184,
            "total_amount": 983,
            "currency": "usd",
            "metadata": {"user_id": "7", "plan_id": "2"},
            "customer": {"id": "cus_polar_1", "external_id": "7", "metadata": {}},
        }
        attrs = _normalise("order.paid", _event("order.paid", order))["data"][
            "attributes"
        ]
        self.assertEqual(attrs["total"], 983)
        self.assertEqual(attrs["order_id"], "ord_1")
        self.assertEqual(attrs["subscription_id"], "sub_polar_1")

    def test_missing_total_does_not_explode(self):
        attrs = _normalise("order.paid", _event("order.paid", {}))["data"]["attributes"]
        self.assertEqual(attrs["total"], 0)

    def test_falls_back_to_the_customer_external_id(self):
        # Polar only documents checkout metadata reaching the subscription for
        # the upgrade flow, so attribution must survive metadata going missing.
        data = _subscription(metadata={})
        cd = _normalise("subscription.created", _event("x", data))["meta"][
            "custom_data"
        ]
        self.assertEqual(cd["user_id"], "7")

    def test_falls_back_to_customer_metadata_for_the_locale(self):
        data = _subscription(
            metadata={},
            customer={"id": "c", "external_id": "7", "metadata": {"locale": "ru"}},
        )
        cd = _normalise("subscription.created", _event("x", data))["meta"][
            "custom_data"
        ]
        self.assertEqual(cd["locale"], "ru")

    def test_plan_is_recovered_from_the_product_when_metadata_is_empty(self):
        plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly-lookup",
            price="7.99",
            currency="USD",
            duration_days=30,
            polar_product_id="prod_lookup",
        )
        data = _subscription(metadata={}, product_id="prod_lookup")
        cd = _normalise("subscription.created", _event("x", data))["meta"][
            "custom_data"
        ]
        self.assertEqual(cd["plan_id"], str(plan.id))


class EventRoutingTests(TestCase):
    def test_canceled_only_flags_and_does_not_revoke(self):
        # Polar's `canceled` means "scheduled": the customer paid for the rest
        # of the period. Routing it to the expired handler would cut off access
        # someone already paid for.
        self.assertIs(
            EVENT_DISPATCH["subscription.canceled"], h.handle_subscription_cancelled
        )

    def test_revoked_is_what_actually_revokes(self):
        self.assertIs(
            EVENT_DISPATCH["subscription.revoked"], h.handle_subscription_expired
        )


@override_settings(POLAR_WEBHOOK_SECRET=SECRET)
class WebhookDeliveryTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _post(self, payload, headers=None, msg_id="msg_1"):
        body = json.dumps(payload).encode()
        return self.client.post(
            URL,
            data=body,
            content_type="application/json",
            headers=headers or _headers(body, msg_id=msg_id),
        )

    def test_rejects_bad_signature_without_running_handler(self):
        payload = _event("subscription.created", _subscription())
        bad = {
            "webhook-id": "msg_bad",
            "webhook-timestamp": str(int(time.time())),
            "webhook-signature": "v1,AAAA",
        }
        with mock.patch.object(h, "handle_subscription_created") as handler:
            r = self._post(payload, headers=bad)
        self.assertEqual(r.status_code, 400)
        handler.assert_not_called()
        self.assertFalse(WebhookEvent.objects.exists())

    def test_duplicate_delivery_runs_handler_once(self):
        payload = _event("subscription.created", _subscription())
        with mock.patch(
            "src.payments.polar_webhook.EVENT_DISPATCH",
            {"subscription.created": mock.Mock()},
        ) as dispatch:
            handler = dispatch["subscription.created"]
            self.assertEqual(self._post(payload).status_code, 200)
            self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(handler.call_count, 1)
        self.assertEqual(WebhookEvent.objects.filter(provider="polar").count(), 1)

    def test_stores_the_original_payload_not_the_normalised_one(self):
        payload = _event("subscription.created", _subscription())
        with mock.patch(
            "src.payments.polar_webhook.EVENT_DISPATCH",
            {"subscription.created": mock.Mock()},
        ):
            self._post(payload)
        evt = WebhookEvent.objects.get(provider="polar")
        self.assertEqual(evt.raw_payload["data"]["status"], "active")
        self.assertNotIn("_provider", evt.raw_payload)

    def test_unhandled_event_is_acknowledged(self):
        r = self._post(_event("benefit.created", {}))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(WebhookEvent.objects.exists())

    def test_missing_webhook_id_is_rejected(self):
        body = json.dumps(_event("subscription.created", _subscription())).encode()
        headers = _headers(body)
        headers.pop("webhook-id")
        r = self.client.post(
            URL, data=body, content_type="application/json", headers=headers
        )
        # No id means no idempotency key, and the signature covers it, so this
        # can only be a malformed delivery.
        self.assertEqual(r.status_code, 400)

    @override_settings(POLAR_WEBHOOK_SECRET="")
    def test_unconfigured_secret_returns_503(self):
        r = self._post(_event("subscription.created", _subscription()))
        self.assertEqual(r.status_code, 503)


@override_settings(POLAR_WEBHOOK_SECRET=SECRET)
class EndToEndPremiumTests(TestCase):
    """A signed Polar delivery must actually grant and revoke premium.

    The unit tests above check signing, normalisation and routing separately;
    this one catches the case where each is individually right but they
    disagree — a field renamed on one side only, which would silently leave a
    paying customer without access.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="payer", email="payer@example.com", password="x"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly-polar",
            price="7.99",
            currency="USD",
            duration_days=30,
            polar_product_id="prod_polar_1",
        )
        self.client = Client()

    def _deliver(self, payload, msg_id):
        body = json.dumps(payload).encode()
        return self.client.post(
            URL,
            data=body,
            content_type="application/json",
            headers=_headers(body, msg_id=msg_id),
        )

    def _sub_event(self, event_type, **overrides):
        data = _subscription(
            id="sub_e2e",
            customer_id="cus_e2e",
            metadata={
                "user_id": str(self.user.id),
                "plan_id": str(self.plan.id),
                "locale": "en",
            },
            customer={"id": "cus_e2e", "external_id": str(self.user.id)},
            **overrides,
        )
        return _event(event_type, data)

    def test_subscription_created_grants_premium(self):
        r = self._deliver(self._sub_event("subscription.created"), "msg_e2e_1")
        self.assertEqual(r.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertTrue(self.user.is_subscription_active())

        sub = self.user.provider_subscription
        self.assertEqual(sub.provider, "polar")  # not "lemonsqueezy"
        self.assertEqual(sub.provider_subscription_id, "sub_e2e")
        self.assertEqual(sub.provider_customer_id, "cus_e2e")

    def test_scheduled_cancellation_keeps_access_until_period_end(self):
        self._deliver(self._sub_event("subscription.created"), "msg_e2e_2")
        r = self._deliver(
            self._sub_event(
                "subscription.canceled",
                status="canceled",
                cancel_at_period_end=True,
                ends_at="2026-09-26T09:00:00Z",
            ),
            "msg_e2e_3",
        )
        self.assertEqual(r.status_code, 200)

        self.user.refresh_from_db()
        sub = self.user.provider_subscription
        self.assertTrue(sub.cancel_at_period_end)
        # Paid through the period: access must NOT be revoked yet.
        self.assertTrue(self.user.is_subscription_active())

    def test_revoked_removes_premium(self):
        self._deliver(self._sub_event("subscription.created"), "msg_e2e_4")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

        r = self._deliver(
            self._sub_event("subscription.revoked", status="canceled"), "msg_e2e_5"
        )
        self.assertEqual(r.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscription_active())

    def test_order_paid_records_the_payment(self):
        self._deliver(self._sub_event("subscription.created"), "msg_e2e_6")
        order = _event(
            "order.paid",
            {
                "id": "ord_e2e",
                "status": "paid",
                "customer_id": "cus_e2e",
                "product_id": "prod_polar_1",
                "subscription_id": "sub_e2e",
                "total_amount": 799,
                "currency": "usd",
                "metadata": {
                    "user_id": str(self.user.id),
                    "plan_id": str(self.plan.id),
                },
                "customer": {"id": "cus_e2e", "external_id": str(self.user.id)},
            },
        )
        self.assertEqual(self._deliver(order, "msg_e2e_7").status_code, 200)

        payment = Payment.objects.get(user=self.user, status="completed")
        # Minor units must become 7.99, not 799.
        self.assertEqual(payment.amount, Decimal("7.99"))
        self.assertEqual(payment.provider, "polar")

    def test_premium_survives_a_dead_broker(self):
        # The welcome mail is queued from an on_commit hook, so by the time it
        # fails the subscription is already committed. Letting the exception
        # escape would 500, make Polar retry a successful delivery, and the
        # mail would never send (its claim is committed too).
        with mock.patch(
            "src.payments.handlers.send_premium_email.delay",
            side_effect=RuntimeError("Retry limit exceeded"),
        ):
            r = self._deliver(self._sub_event("subscription.created"), "msg_broker")

        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNotNone(
            WebhookEvent.objects.get(event_id="msg_broker").processed_at
        )
