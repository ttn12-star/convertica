"""Paddle webhook receiver.

Paddle's payloads are shaped differently from Lemon Squeezy's (flat `data`
instead of `data.attributes`, amounts as minor-unit strings, `custom_data` on
the object rather than in `meta`). Rather than duplicate 450 lines of
subscription logic, this module normalises an event into the shape
`src.payments.handlers` already consumes and reuses those handlers, stamping
`_provider` so rows are written against the right provider.

Docs: https://developer.paddle.com/webhooks/overview
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from src.payments import handlers as h
from src.payments.webhook import process_event
from src.payments.webhook_security import verify_paddle_signature

logger = logging.getLogger(__name__)

# Paddle status -> the vocabulary handlers.py already speaks (Lemon Squeezy's).
_STATUS_MAP = {
    "trialing": "on_trial",
    "canceled": "cancelled",
}

EVENT_DISPATCH = {
    "subscription.created": h.handle_subscription_created,
    "subscription.updated": h.handle_subscription_updated,
    # NOT handle_subscription_cancelled. Paddle fires subscription.canceled when
    # the cancellation takes EFFECT (status is already "canceled"), whereas Lemon
    # Squeezy fired subscription_cancelled when one was merely scheduled. The
    # scheduled case arrives here as subscription.updated carrying
    # scheduled_change, which _normalise turns into cancel_at_period_end.
    # Routing this to the "cancelled" handler would leave premium switched on
    # forever, since nothing else would ever revoke it.
    "subscription.canceled": h.handle_subscription_expired,
    "subscription.paused": h.handle_subscription_paused,
    "subscription.resumed": h.handle_subscription_resumed,
    "subscription.past_due": h.handle_subscription_payment_failed,
    "transaction.completed": h.handle_subscription_payment_success,
    "transaction.payment_failed": h.handle_subscription_payment_failed,
}


def _minor_units_to_int(value) -> int:
    """Paddle sends money as a minor-unit string ("799"). Handlers want cents."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalise(event_type: str, payload: dict) -> dict:
    """Convert a Paddle event into the payload shape handlers.py expects."""
    data = payload.get("data", {}) or {}
    custom_data = data.get("custom_data") or {}

    attrs: dict = {
        "status": _STATUS_MAP.get(data.get("status"), data.get("status") or "active"),
        "customer_id": data.get("customer_id") or "",
    }

    if event_type.startswith("subscription."):
        period = data.get("current_billing_period") or {}
        attrs["created_at"] = data.get("started_at") or period.get("starts_at")
        attrs["renews_at"] = period.get("ends_at")

        scheduled = data.get("scheduled_change") or {}
        if scheduled.get("action") == "cancel":
            # Handlers read `cancelled` (bool) and prefer `ends_at` for the
            # period end, which is exactly when access should stop.
            attrs["cancelled"] = True
            attrs["ends_at"] = scheduled.get("effective_at") or period.get("ends_at")
        data_id = data.get("id") or ""
    else:
        # transaction.*: the money events.
        totals = (data.get("details") or {}).get("totals") or {}
        attrs["total"] = _minor_units_to_int(totals.get("grand_total"))
        attrs["order_id"] = data.get("id") or ""
        attrs["subscription_id"] = data.get("subscription_id") or ""
        data_id = data.get("id") or ""

    return {
        "_provider": "paddle",
        "meta": {"custom_data": custom_data},
        "data": {"id": data_id, "attributes": attrs},
    }


@csrf_exempt
@require_http_methods(["POST"])
def paddle_webhook(request):
    secret = getattr(settings, "PADDLE_WEBHOOK_SECRET", "") or ""
    if not secret:
        logger.error(
            "Paddle webhook called but PADDLE_WEBHOOK_SECRET unset",
            extra={"event": "paddle_webhook_secret_missing"},
        )
        return HttpResponse("Webhook not configured", status=503)

    body = request.body
    sig = request.headers.get("Paddle-Signature", "") or ""
    if not verify_paddle_signature(body, sig, secret):
        logger.warning(
            "Paddle webhook signature verification failed",
            extra={"event": "paddle_webhook_bad_signature"},
        )
        return HttpResponse("Invalid signature", status=400)

    try:
        payload = json.loads(body)
    except ValueError:
        return HttpResponse("Invalid JSON", status=400)

    event_type = payload.get("event_type") or ""
    # Paddle gives every delivery a real event id, so idempotency needs no
    # synthesising (unlike Lemon Squeezy, where we had to build one).
    event_id = payload.get("event_id") or payload.get("notification_id") or ""
    if not event_id:
        logger.warning(
            "Paddle webhook without event_id",
            extra={"event": "paddle_webhook_no_event_id", "event_type": event_type},
        )
        return HttpResponse("Missing event id", status=400)

    handler = EVENT_DISPATCH.get(event_type)
    if not handler:
        logger.info(
            "Paddle webhook: unhandled event",
            extra={"event": "paddle_webhook_unhandled", "event_type": event_type},
        )
        return HttpResponse("OK")

    return process_event(
        provider="paddle",
        event_id=event_id,
        event_type=event_type,
        payload=_normalise(event_type, payload),
        # Store what Paddle actually sent, not our lossy normalisation of it.
        raw_payload=payload,
        handler=handler,
        livemode=getattr(settings, "PADDLE_ENV", "sandbox") == "production",
    )
