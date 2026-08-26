"""Polar webhook receiver.

Polar's payloads are shaped differently from Lemon Squeezy's (a flat object
under `data`, amounts as integer minor units, `metadata` on the object rather
than in `meta`). Rather than duplicate the subscription logic, this module
normalises an event into the shape `src.payments.handlers` already consumes and
reuses those handlers, stamping `_provider` so rows are written against the
right provider. Same approach as `src.payments.paddle_webhook`.

Object fields come from Polar's own OpenAPI schema (Subscription, Order) rather
than from prose docs, which omit the payload shapes entirely.

Docs: https://polar.sh/docs/integrate/webhooks
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
from src.payments.webhook_security import verify_polar_signature

logger = logging.getLogger(__name__)

# Polar status -> the vocabulary handlers.py already speaks (Lemon Squeezy's).
# `incomplete` means the first payment has not landed yet, which is what LS
# called `unpaid`: no premium is granted for either.
_STATUS_MAP = {
    "trialing": "on_trial",
    "canceled": "cancelled",
    "incomplete": "unpaid",
    "incomplete_expired": "unpaid",
}

EVENT_DISPATCH = {
    "subscription.created": h.handle_subscription_created,
    # `active` arrives once the first payment clears; `cycled` on each renewal.
    # Both only move status and the period window, which is what update does.
    "subscription.active": h.handle_subscription_updated,
    "subscription.updated": h.handle_subscription_updated,
    "subscription.cycled": h.handle_subscription_updated,
    # Polar splits what Paddle conflated: `canceled` is the cancellation being
    # SCHEDULED (the customer keeps access to the end of the paid period, which
    # is Lemon Squeezy's `subscription_cancelled` semantics), and `revoked` is
    # access actually ending. Routing `canceled` to the expired handler would
    # cut off a customer who has already paid for the rest of the month.
    "subscription.canceled": h.handle_subscription_cancelled,
    "subscription.revoked": h.handle_subscription_expired,
    "subscription.uncanceled": h.handle_subscription_resumed,
    "subscription.past_due": h.handle_subscription_payment_failed,
    "order.paid": h.handle_subscription_payment_success,
    "order.refunded": h.handle_subscription_payment_refunded,
}


def _plan_id_for_product(product_id: str) -> str:
    """Map a Polar product back to our plan row.

    The fallback for a missing `plan_id` in metadata. Imported lazily so the
    module stays importable before the app registry is ready.
    """
    if not product_id:
        return ""
    from src.users.models import SubscriptionPlan

    plan_id = (
        SubscriptionPlan.objects.filter(polar_product_id=product_id)
        .values_list("id", flat=True)
        .first()
    )
    return str(plan_id) if plan_id else ""


def _custom_data(data: dict) -> dict:
    """Rebuild the checkout's custom data, with fallbacks.

    Polar documents metadata being copied onto the subscription only for the
    upgrade-an-existing-subscription flow, so for a fresh checkout we cannot
    assume `data.metadata` survives. Every checkout therefore also carries
    `external_customer_id` and `customer_metadata`, and attribution falls back
    to those, then to resolving the plan from the product.
    """
    metadata = data.get("metadata") or {}
    customer = data.get("customer") or {}
    customer_metadata = customer.get("metadata") or {}

    user_id = (
        str(metadata.get("user_id") or "")
        or str(customer.get("external_id") or "")
        or str(customer_metadata.get("user_id") or "")
    )
    plan_id = str(metadata.get("plan_id") or "") or _plan_id_for_product(
        str(data.get("product_id") or "")
    )
    locale = str(metadata.get("locale") or "") or str(
        customer_metadata.get("locale") or ""
    )

    out = {"user_id": user_id, "plan_id": plan_id}
    if locale:
        out["locale"] = locale
    return out


def _normalise(event_type: str, payload: dict) -> dict:
    """Convert a Polar event into the payload shape handlers.py expects."""
    data = payload.get("data", {}) or {}
    status = data.get("status")

    attrs: dict = {
        "status": _STATUS_MAP.get(status, status or "active"),
        "customer_id": str(data.get("customer_id") or ""),
    }

    if event_type.startswith("subscription."):
        data_id = str(data.get("id") or "")
        attrs["created_at"] = data.get("started_at") or data.get("current_period_start")
        attrs["renews_at"] = data.get("current_period_end")
        # handle_subscription_payment_failed reads the subscription id off
        # attrs, not off data.id, so past_due needs it spelled out here.
        attrs["subscription_id"] = data_id

        if data.get("cancel_at_period_end"):
            # Handlers read `cancelled` (bool) and prefer `ends_at` for the
            # period end, which is exactly when access should stop.
            attrs["cancelled"] = True
            attrs["ends_at"] = data.get("ends_at") or data.get("current_period_end")
    else:
        # order.*: the money events. `total_amount` is what the customer was
        # actually charged (subtotal - discount + tax), already in minor units.
        data_id = str(data.get("id") or "")
        attrs["total"] = int(data.get("total_amount") or 0)
        attrs["order_id"] = data_id
        attrs["subscription_id"] = str(data.get("subscription_id") or "")

    return {
        "_provider": "polar",
        "meta": {"custom_data": _custom_data(data)},
        "data": {"id": data_id, "attributes": attrs},
    }


@csrf_exempt
@require_http_methods(["POST"])
def polar_webhook(request):
    secret = getattr(settings, "POLAR_WEBHOOK_SECRET", "") or ""
    if not secret:
        logger.error(
            "Polar webhook called but POLAR_WEBHOOK_SECRET unset",
            extra={"event": "polar_webhook_secret_missing"},
        )
        return HttpResponse("Webhook not configured", status=503)

    body = request.body
    if not verify_polar_signature(body, request.headers, secret):
        logger.warning(
            "Polar webhook signature verification failed",
            extra={"event": "polar_webhook_bad_signature"},
        )
        return HttpResponse("Invalid signature", status=400)

    try:
        payload = json.loads(body)
    except ValueError:
        return HttpResponse("Invalid JSON", status=400)

    event_type = payload.get("type") or ""
    # Standard Webhooks gives every delivery a unique id in the header, and
    # retries reuse it — exactly what idempotency needs, so nothing has to be
    # synthesised the way it was for Lemon Squeezy.
    event_id = request.headers.get("webhook-id", "") or ""
    if not event_id:
        logger.warning(
            "Polar webhook without webhook-id header",
            extra={"event": "polar_webhook_no_event_id", "event_type": event_type},
        )
        return HttpResponse("Missing event id", status=400)

    handler = EVENT_DISPATCH.get(event_type)
    if not handler:
        logger.info(
            "Polar webhook: unhandled event",
            extra={"event": "polar_webhook_unhandled", "event_type": event_type},
        )
        return HttpResponse("OK")

    return process_event(
        provider="polar",
        event_id=event_id,
        event_type=event_type,
        payload=_normalise(event_type, payload),
        # Store what Polar actually sent, not our lossy normalisation of it.
        raw_payload=payload,
        handler=handler,
        livemode=getattr(settings, "POLAR_ENV", "sandbox") == "production",
    )
