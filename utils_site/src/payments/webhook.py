"""Lemon Squeezy webhook receiver.

Verifies HMAC signature, ensures idempotency via WebhookEvent, and dispatches
event payloads to handler functions.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from src.payments import handlers as h
from src.payments.webhook_security import verify_lemonsqueezy_signature
from src.users.models import WebhookEvent

logger = logging.getLogger(__name__)

EVENT_DISPATCH = {
    "subscription_created": h.handle_subscription_created,
    "subscription_updated": h.handle_subscription_updated,
    "subscription_cancelled": h.handle_subscription_cancelled,
    "subscription_resumed": h.handle_subscription_resumed,
    "subscription_expired": h.handle_subscription_expired,
    "subscription_paused": h.handle_subscription_paused,
    "subscription_unpaused": h.handle_subscription_unpaused,
    "subscription_payment_success": h.handle_subscription_payment_success,
    "subscription_payment_failed": h.handle_subscription_payment_failed,
    "subscription_payment_refunded": h.handle_subscription_payment_refunded,
    "order_created": h.handle_order_created,
    "order_refunded": h.handle_order_refunded,
}


def _build_event_id(payload: dict, request) -> str:
    """Derive a stable event id for idempotency.

    LS doesn't include a true event_id at top level — but each webhook delivery
    has a stable hash of (event_name, data.id, data.attributes.updated_at?).
    We construct: <event_name>:<data.type>:<data.id>:<request_id_or_payload_hash>.
    """
    meta = payload.get("meta", {}) or {}
    data = payload.get("data", {}) or {}
    event_name = meta.get("event_name", "")
    data_type = data.get("type", "")
    data_id = data.get("id", "")
    request_id = request.headers.get("X-Request-Id", "")
    if request_id:
        return f"{event_name}:{data_type}:{data_id}:{request_id}"
    # Fallback: use updated_at or current_period_end to discriminate renewals
    attrs = data.get("attributes", {}) or {}
    discriminator = (
        attrs.get("updated_at")
        or attrs.get("renews_at")
        or attrs.get("created_at")
        or ""
    )
    return f"{event_name}:{data_type}:{data_id}:{discriminator}"


@csrf_exempt
@require_http_methods(["POST"])
def lemonsqueezy_webhook(request):
    secret = getattr(settings, "LEMONSQUEEZY_WEBHOOK_SECRET", "") or ""
    if not secret:
        logger.error(
            "LS webhook called but LEMONSQUEEZY_WEBHOOK_SECRET unset",
            extra={"event": "ls_webhook_secret_missing"},
        )
        return HttpResponse("Webhook not configured", status=503)

    body = request.body
    sig = request.headers.get("X-Signature", "") or ""
    if not verify_lemonsqueezy_signature(body, sig, secret):
        logger.warning(
            "LS webhook signature verification failed",
            extra={"event": "ls_webhook_bad_signature"},
        )
        return HttpResponse("Invalid signature", status=400)

    try:
        payload = json.loads(body)
    except ValueError:
        return HttpResponse("Invalid JSON", status=400)

    event_name = (payload.get("meta") or {}).get("event_name") or ""
    event_id = _build_event_id(payload, request)

    handler = EVENT_DISPATCH.get(event_name)
    if not handler:
        logger.info(
            "LS webhook: unhandled event",
            extra={"event": "ls_webhook_unhandled", "event_name": event_name},
        )
        return HttpResponse("OK")

    # Idempotency
    try:
        evt, created = WebhookEvent.objects.get_or_create(
            provider="lemonsqueezy",
            event_id=event_id,
            defaults={
                "event_type": event_name,
                "livemode": not bool((payload.get("meta") or {}).get("test_mode")),
                "processing": True,
                "raw_payload": payload,
            },
        )
    except IntegrityError:
        return HttpResponse("OK")

    if not created:
        if evt.processed_at is not None:
            return HttpResponse("OK")
        if evt.processing:
            # Another worker is currently processing — let LS retry later.
            return HttpResponse("OK")
        # Previous attempt failed — allow retry
        evt.processing = True
        evt.save(update_fields=["processing"])

    try:
        handler(payload)
        evt.processing = False
        evt.processed_at = timezone.now()
        evt.last_error = ""
        evt.save(update_fields=["processing", "processed_at", "last_error"])
        return HttpResponse("OK")
    except Exception as e:
        logger.exception("LS webhook handler failed")
        evt.processing = False
        evt.last_error = str(e)[:2000]
        evt.save(update_fields=["processing", "last_error"])
        # Return 500 so LS retries — but only if the error is recoverable.
        return HttpResponse("Internal error", status=500)
