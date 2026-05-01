"""Lemon Squeezy webhook event handlers.

Each handler takes the parsed JSON payload (dict) and applies provider-agnostic
operations on User/UserSubscription/Payment. Handlers are atomic and idempotent
at the call-site (the dispatcher de-duplicates via WebhookEvent).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription

logger = logging.getLogger(__name__)


# --- Helpers ---


def _custom_data(payload: dict) -> dict:
    return payload.get("meta", {}).get("custom_data", {}) or {}


def _resolve_user_and_plan(
    payload: dict,
) -> tuple[User | None, SubscriptionPlan | None]:
    cd = _custom_data(payload)
    user_id = cd.get("user_id")
    plan_id = cd.get("plan_id")
    user = User.objects.filter(id=user_id).first() if user_id else None
    plan = SubscriptionPlan.objects.filter(id=plan_id).first() if plan_id else None
    if not user:
        logger.warning(
            "LS webhook: user not found",
            extra={"event": "ls_webhook_user_missing", "custom_data": cd},
        )
    if not plan:
        logger.warning(
            "LS webhook: plan not found",
            extra={"event": "ls_webhook_plan_missing", "custom_data": cd},
        )
    return user, plan


def _parse_dt(value: str | None):
    if not value:
        return None
    # LS sends ISO-8601 with microseconds + Z timezone
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _attrs(payload: dict) -> dict:
    return payload.get("data", {}).get("attributes", {}) or {}


def _data_id(payload: dict) -> str:
    return str(payload.get("data", {}).get("id", "") or "")


# --- Subscription handlers ---


@transaction.atomic
def handle_subscription_created(payload: dict) -> None:
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    attrs = _attrs(payload)
    sub_id = _data_id(payload)
    customer_id = str(attrs.get("customer_id") or "")
    period_start = _parse_dt(attrs.get("created_at")) or timezone.now()
    period_end = _parse_dt(attrs.get("renews_at"))
    cancel_at_period_end = bool(attrs.get("cancelled"))
    status = attrs.get("status") or "active"

    UserSubscription.upsert_from_event(
        user=user,
        plan=plan,
        provider="lemonsqueezy",
        provider_subscription_id=sub_id,
        provider_customer_id=customer_id,
        status=status,
        current_period_start=period_start,
        current_period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
    )
    if status in ("active", "on_trial"):
        user.activate_premium(
            plan=plan,
            period_start=period_start,
            period_end=period_end,
            provider="lemonsqueezy",
            provider_subscription_id=sub_id,
            provider_customer_id=customer_id,
        )


@transaction.atomic
def handle_subscription_updated(payload: dict) -> None:
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    attrs = _attrs(payload)
    sub_id = _data_id(payload)
    customer_id = str(attrs.get("customer_id") or "")
    status = attrs.get("status") or "active"
    cancel_at_period_end = bool(attrs.get("cancelled"))
    period_end = _parse_dt(attrs.get("ends_at")) or _parse_dt(attrs.get("renews_at"))

    sub_qs = UserSubscription.objects.filter(
        provider="lemonsqueezy", provider_subscription_id=sub_id
    )
    sub = sub_qs.first()
    period_start = sub.current_period_start if sub else timezone.now()

    UserSubscription.upsert_from_event(
        user=user,
        plan=plan,
        provider="lemonsqueezy",
        provider_subscription_id=sub_id,
        provider_customer_id=customer_id,
        status=status,
        current_period_start=period_start,
        current_period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
    )

    if status in ("active", "on_trial") and period_end:
        user.activate_premium(
            plan=plan,
            period_start=period_start,
            period_end=period_end,
            provider="lemonsqueezy",
            provider_subscription_id=sub_id,
            provider_customer_id=customer_id,
        )
    elif status in ("expired", "unpaid"):
        user.deactivate_premium(reason="expired")


@transaction.atomic
def handle_subscription_cancelled(payload: dict) -> None:
    """Mark cancel_at_period_end. Premium remains until period end."""
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    attrs = _attrs(payload)
    sub_id = _data_id(payload)
    period_end = _parse_dt(attrs.get("ends_at")) or _parse_dt(attrs.get("renews_at"))
    UserSubscription.objects.filter(
        provider="lemonsqueezy", provider_subscription_id=sub_id
    ).update(
        status="cancelled",
        cancel_at_period_end=True,
        current_period_end=period_end or timezone.now(),
    )
    # Do NOT deactivate premium yet — wait for subscription_expired.


@transaction.atomic
def handle_subscription_resumed(payload: dict) -> None:
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    sub_id = _data_id(payload)
    UserSubscription.objects.filter(
        provider="lemonsqueezy", provider_subscription_id=sub_id
    ).update(status="active", cancel_at_period_end=False)


@transaction.atomic
def handle_subscription_expired(payload: dict) -> None:
    user, _plan = _resolve_user_and_plan(payload)
    if not user:
        return
    sub_id = _data_id(payload)
    UserSubscription.objects.filter(
        provider="lemonsqueezy", provider_subscription_id=sub_id
    ).update(status="expired")
    user.deactivate_premium(reason="expired")


@transaction.atomic
def handle_subscription_paused(payload: dict) -> None:
    user, _plan = _resolve_user_and_plan(payload)
    if not user:
        return
    sub_id = _data_id(payload)
    UserSubscription.objects.filter(
        provider="lemonsqueezy", provider_subscription_id=sub_id
    ).update(status="paused")
    grace_days = int(getattr(settings, "PAYMENT_PAST_DUE_GRACE_DAYS", 0) or 0)
    if grace_days > 0:
        user.apply_grace(until=timezone.now() + timedelta(days=grace_days))
    else:
        user.deactivate_premium(reason="cancelled")


@transaction.atomic
def handle_subscription_unpaused(payload: dict) -> None:
    handle_subscription_resumed(payload)


@transaction.atomic
def handle_subscription_payment_success(payload: dict) -> None:
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    attrs = _attrs(payload)
    order_id = str(attrs.get("order_id") or _data_id(payload))
    amount_cents = int(attrs.get("total") or 0)
    Payment.record_completed(
        user=user,
        plan=plan,
        amount=Decimal(amount_cents) / Decimal(100),
        external_payment_id=order_id,
        provider="lemonsqueezy",
    )


@transaction.atomic
def handle_subscription_payment_failed(payload: dict) -> None:
    user, _plan = _resolve_user_and_plan(payload)
    if not user:
        return
    sub_id = str(_attrs(payload).get("subscription_id") or "")
    if sub_id:
        UserSubscription.objects.filter(
            provider="lemonsqueezy", provider_subscription_id=sub_id
        ).update(status="past_due")
    grace_days = int(getattr(settings, "PAYMENT_PAST_DUE_GRACE_DAYS", 0) or 0)
    if grace_days > 0:
        user.apply_grace(until=timezone.now() + timedelta(days=grace_days))
    else:
        user.deactivate_premium(reason="expired")


@transaction.atomic
def handle_subscription_payment_refunded(payload: dict) -> None:
    user, _plan = _resolve_user_and_plan(payload)
    if not user:
        return
    attrs = _attrs(payload)
    order_id = str(attrs.get("order_id") or _data_id(payload))
    Payment.objects.filter(payment_id=order_id).update(
        status="refunded", processed_at=timezone.now()
    )
    user.deactivate_premium(reason="refunded")


# --- Order handlers (Lifetime / one-time) ---


@transaction.atomic
def handle_order_created(payload: dict) -> None:
    user, plan = _resolve_user_and_plan(payload)
    if not user or not plan:
        return
    attrs = _attrs(payload)
    order_id = _data_id(payload)
    customer_id = str(attrs.get("customer_id") or "")
    amount_cents = int(attrs.get("total") or 0)

    Payment.record_completed(
        user=user,
        plan=plan,
        amount=Decimal(amount_cents) / Decimal(100),
        external_payment_id=order_id,
        provider="lemonsqueezy",
    )
    user.activate_premium(
        plan=plan,
        period_start=timezone.now(),
        period_end=(
            None
            if plan.is_lifetime
            else (timezone.now() + timedelta(days=plan.duration_days))
        ),
        provider="lemonsqueezy",
        provider_subscription_id="",
        provider_customer_id=customer_id,
    )


@transaction.atomic
def handle_order_refunded(payload: dict) -> None:
    user, _plan = _resolve_user_and_plan(payload)
    if not user:
        return
    order_id = _data_id(payload)
    Payment.objects.filter(payment_id=order_id).update(
        status="refunded", processed_at=timezone.now()
    )
    user.deactivate_premium(reason="refunded")
