"""Payments views (Lemon Squeezy)."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from src.payments.lemonsqueezy import LemonSqueezyClient, LemonSqueezyError
from src.users.models import Payment, SubscriptionPlan, UserSubscription

logger = logging.getLogger(__name__)


def _client() -> LemonSqueezyClient:
    return LemonSqueezyClient()


@login_required
@require_http_methods(["POST"])
def create_checkout_session(request):
    """Generate a Lemon Squeezy hosted checkout URL for the requested plan."""
    if not getattr(settings, "PAYMENTS_ENABLED", True):
        return JsonResponse(
            {"error": "Payments are temporarily unavailable."}, status=503
        )

    if not settings.LEMONSQUEEZY_API_KEY or not settings.LEMONSQUEEZY_STORE_ID:
        return JsonResponse({"error": "Lemon Squeezy is not configured."}, status=503)

    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    plan_slug = data.get("plan_slug")
    if not plan_slug:
        return JsonResponse({"error": "plan_slug is required"}, status=400)

    try:
        plan = SubscriptionPlan.objects.get(slug=plan_slug, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({"error": "Plan not found"}, status=404)

    if not plan.ls_variant_id:
        return JsonResponse(
            {"error": "Plan is not configured with Lemon Squeezy variant"},
            status=503,
        )

    user = request.user

    # Already subscribed → redirect to portal.
    existing = (
        UserSubscription.objects.filter(user=user)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if existing and (
        existing.is_active()
        or (
            existing.status in {"past_due", "unpaid"}
            and existing.current_period_end
            and existing.current_period_end > timezone.now()
        )
    ):
        portal_url = ""
        if existing.provider_customer_id:
            try:
                customer = _client().get_customer(existing.provider_customer_id)
                portal_url = (customer.get("urls") or {}).get("customer_portal", "")
            except LemonSqueezyError:
                portal_url = ""
        return JsonResponse(
            {
                "error": (
                    "You already have an active subscription. "
                    "Manage it in the customer portal."
                ),
                "portal_url": portal_url,
                "manage_url": request.build_absolute_uri(
                    reverse("users:manage_subscription")
                ),
            },
            status=409,
        )

    success_url = request.build_absolute_uri(reverse("payments:payment_success"))

    try:
        result = _client().create_checkout(
            store_id=settings.LEMONSQUEEZY_STORE_ID,
            variant_id=plan.ls_variant_id,
            custom_data={
                "user_id": str(user.id),
                "plan_id": str(plan.id),
            },
            success_url=success_url,
            email=user.email,
            locale=getattr(request, "LANGUAGE_CODE", "en") or "en",
        )
    except LemonSqueezyError as e:
        logger.error(f"LS create_checkout failed: {e}")
        return JsonResponse({"error": "Checkout creation failed"}, status=502)

    return JsonResponse(
        {
            "checkout_id": result.get("id", ""),
            "checkout_url": result.get("url", ""),
        }
    )


@login_required
def payment_success(request):
    """Show success page using DB as source of truth.

    Webhook may have already activated premium, or may arrive shortly.
    The view doesn't try to reach LS — DB is sufficient because lemon.js
    only redirects here after the LS-side payment confirmation.
    """
    user = request.user
    user.refresh_from_db()

    subscription = (
        UserSubscription.objects.filter(user=user)
        .select_related("plan")
        .order_by("-updated_at", "-created_at")
        .first()
    )
    payment = (
        Payment.objects.filter(user=user, status="completed")
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    plan = (subscription.plan if subscription else None) or (
        payment.plan if payment else None
    )
    return render(
        request,
        "payments/success.html",
        {
            "plan": plan,
            "subscription": subscription,
            "payment": payment,
            "is_premium_active": user.is_premium and user.is_subscription_active(),
        },
    )


@login_required
def payment_cancel(request):
    return render(request, "payments/cancel.html")
