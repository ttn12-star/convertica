import json
import logging
from datetime import UTC, datetime

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from src.users.models import (
    Payment,
    StripeWebhookEvent,
    SubscriptionPlan,
    User,
    UserSubscription,
)

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def _ensure_stripe_sdk_ready():
    if (
        getattr(stripe, "apps", None) is not None
        and getattr(stripe, "billing_portal", None) is not None
        and getattr(stripe, "checkout", None) is not None
        and getattr(stripe, "test_helpers", None) is not None
    ):
        return
    try:
        import importlib

        for module_name in (
            "stripe.apps",
            "stripe.billing_portal",
            "stripe.checkout",
            "stripe.climate",
            "stripe.financial_connections",
            "stripe.identity",
            "stripe.issuing",
            "stripe.radar",
            "stripe.reporting",
            "stripe.sigma",
            "stripe.tax",
            "stripe.terminal",
            "stripe.test_helpers",
            "stripe.treasury",
        ):
            importlib.import_module(module_name)
    except Exception:
        return


def _create_billing_portal_session(user: User, return_url: str | None = None):
    """Create a Stripe Billing Portal session for an existing customer."""
    _ensure_stripe_sdk_ready()
    if not getattr(stripe, "billing_portal", None):
        return None
    if not user.stripe_customer_id:
        return None
    try:
        return stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )
    except Exception:
        return None


def _past_due_grace_days() -> int:
    return int(getattr(settings, "STRIPE_PAST_DUE_GRACE_DAYS", 0) or 0)


def _is_support_subscription_from_stripe(subscription_obj) -> bool:
    return bool(
        getattr(subscription_obj, "metadata", None)
        and subscription_obj.metadata.get("kind") == "support"
    )


def _stripe_obj_get(obj, key, default=None):
    """Safely read Stripe object fields.

    Stripe objects are dict-like; some keys (e.g. 'items') collide with dict methods.
    """
    try:
        getter = getattr(obj, "get", None)
        if callable(getter):
            return getter(key, default)
    except Exception:
        return default
    return getattr(obj, key, default)


def _dt_from_timestamp(ts):
    """Convert timestamp or datetime to timezone-aware datetime.

    Handles various input types:
    - Unix timestamp (int or float)
    - datetime objects (naive or aware)
    - None
    """
    try:
        if ts is None:
            return None

        # If it's already a datetime object
        if isinstance(ts, datetime):
            # If naive, make it timezone-aware using UTC
            if ts.tzinfo is None:
                return ts.replace(tzinfo=UTC)
            # If aware, convert to UTC
            return ts.astimezone(UTC)

        # Convert timestamp to datetime
        return datetime.fromtimestamp(int(ts), tz=UTC)
    except (ValueError, TypeError, OverflowError):
        return None


def _resolve_plan_from_stripe_subscription(subscription_obj):
    plan_id = None
    if getattr(subscription_obj, "metadata", None):
        plan_id = subscription_obj.metadata.get("plan_id")
    if plan_id:
        try:
            return SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return None

    try:
        items = _stripe_obj_get(subscription_obj, "items")
        data = _stripe_obj_get(items, "data") or []
        if data:
            price = _stripe_obj_get(data[0], "price")
            price_id = _stripe_obj_get(price, "id")
            if price_id:
                return SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
    except Exception:
        return None
    return None


def _sync_user_from_subscription(
    user: User, stripe_status: str, period_start, period_end
):
    now = timezone.now()
    grace_days = _past_due_grace_days()

    if stripe_status in {"active", "trialing"}:
        if period_start and not user.subscription_start_date:
            user.subscription_start_date = _dt_from_timestamp(period_start)
        if period_end:
            user.subscription_end_date = _dt_from_timestamp(period_end)
        user.is_premium = True
        user._subscription_changed = True
        user.save(
            update_fields=[
                "subscription_start_date",
                "subscription_end_date",
                "is_premium",
            ]
        )
        return

    if stripe_status == "past_due":
        if grace_days <= 0:
            user.cancel_subscription()
            if user.is_premium:
                user.is_premium = False
                user._subscription_changed = True
                user.save(update_fields=["is_premium"])
            return

        grace_until = now + timezone.timedelta(days=grace_days)
        current_end = user.subscription_end_date or now
        if current_end < grace_until:
            user.subscription_end_date = grace_until
        user.is_premium = True
        user._subscription_changed = True
        user.save(update_fields=["subscription_end_date", "is_premium"])
        return

    user.cancel_subscription()
    if user.is_premium:
        user.is_premium = False
        user._subscription_changed = True
        user.save(update_fields=["is_premium"])


def handle_subscription_updated(subscription_obj):
    """Handle Stripe customer.subscription.updated event."""
    try:
        if _is_support_subscription_from_stripe(subscription_obj):
            return

        stripe_subscription_id = getattr(subscription_obj, "id", None)
        stripe_customer_id = getattr(subscription_obj, "customer", None)
        stripe_status = getattr(subscription_obj, "status", "") or ""
        cancel_at_period_end = bool(
            getattr(subscription_obj, "cancel_at_period_end", False)
        )
        period_start = getattr(subscription_obj, "current_period_start", None)
        period_end = getattr(subscription_obj, "current_period_end", None)

        if not period_start or not period_end:
            items = _stripe_obj_get(subscription_obj, "items")
            data = _stripe_obj_get(items, "data") or []
            if data:
                period_start = period_start or _stripe_obj_get(
                    data[0], "current_period_start"
                )
                period_end = period_end or _stripe_obj_get(
                    data[0], "current_period_end"
                )

        user = None
        if getattr(subscription_obj, "metadata", None):
            user_id = subscription_obj.metadata.get("user_id")
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    user = None
        if not user and stripe_customer_id:
            user = User.objects.filter(stripe_customer_id=stripe_customer_id).first()

        user_subscription = None
        if stripe_subscription_id:
            user_subscription = (
                UserSubscription.objects.filter(
                    stripe_subscription_id=stripe_subscription_id
                )
                .select_related("user")
                .first()
            )
        if not user and user_subscription:
            user = user_subscription.user
        if not user:
            logger.warning("Stripe subscription update without resolvable user")
            return

        plan = _resolve_plan_from_stripe_subscription(subscription_obj)
        if not plan and user_subscription and user_subscription.plan:
            plan = user_subscription.plan

        defaults = {
            "plan": plan,
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_customer_id": stripe_customer_id,
            "status": stripe_status,
            "cancel_at_period_end": cancel_at_period_end,
        }
        if period_start:
            defaults["current_period_start"] = _dt_from_timestamp(period_start)
        if period_end:
            defaults["current_period_end"] = _dt_from_timestamp(period_end)

        # Final fallback: if Stripe still doesn't provide a period, derive from plan duration.
        if (not period_start or not period_end) and plan:
            now = timezone.now()
            defaults.setdefault("current_period_start", now)
            defaults.setdefault(
                "current_period_end", now + timezone.timedelta(days=plan.duration_days)
            )
            period_start = int(defaults["current_period_start"].timestamp())
            period_end = int(defaults["current_period_end"].timestamp())

        UserSubscription.objects.update_or_create(user=user, defaults=defaults)

        _sync_user_from_subscription(user, stripe_status, period_start, period_end)

    except Exception as e:
        logger.error(f"Handle subscription updated error: {e}")


def handle_checkout_session_expired(session):
    """Handle Stripe checkout.session.expired (analytics/logging only)."""
    try:
        if (
            getattr(session, "metadata", None)
            and session.metadata.get("kind") == "support"
        ):
            return
        logger.info(
            "Stripe checkout session expired",
            extra={
                "session_id": getattr(session, "id", None),
                "customer": getattr(session, "customer", None),
                "mode": getattr(session, "mode", None),
            },
        )
    except Exception as e:
        logger.error(f"Handle checkout session expired error: {e}")


def handle_charge_refunded(charge):
    """Map Stripe refunds/disputes to Payment.status='refunded' when possible."""
    try:
        payment_id = getattr(charge, "payment_intent", None) or getattr(
            charge, "id", None
        )
        if not payment_id:
            return

        payment = Payment.objects.filter(payment_id=payment_id).first()
        if not payment:
            return

        if payment.status != "refunded":
            payment.status = "refunded"
            payment.processed_at = timezone.now()
            payment.save(update_fields=["status", "processed_at"])

    except Exception as e:
        logger.error(f"Handle charge refunded error: {e}")


def handle_charge_dispute_created(dispute):
    """Treat disputes like refunds to revoke premium entitlement."""
    try:
        charge_id = getattr(dispute, "charge", None)
        if not charge_id:
            return
        _ensure_stripe_sdk_ready()
        charge = stripe.Charge.retrieve(charge_id)
        handle_charge_refunded(charge)
    except Exception as e:
        logger.error(f"Handle dispute created error: {e}")


@require_http_methods(["POST"])
def create_support_checkout_session(request):
    """Create Stripe checkout session for a support payment (no Premium entitlement)."""
    try:
        if not bool(getattr(settings, "PAYMENTS_ENABLED", True)):
            return JsonResponse(
                {"error": "Payments are temporarily unavailable."},
                status=503,
            )
        _ensure_stripe_sdk_ready()
        if not getattr(settings, "STRIPE_SECRET_KEY", None):
            return JsonResponse(
                {
                    "error": "Stripe is not configured. Please set STRIPE_SECRET_KEY (and STRIPE_PUBLISHABLE_KEY) and try again."
                },
                status=503,
            )
        if not getattr(stripe, "checkout", None) or not getattr(
            stripe.checkout, "Session", None
        ):
            logger.error("Stripe checkout API is unavailable (stripe.checkout.Session)")
            return JsonResponse(
                {"error": "Stripe checkout API is unavailable on the server."},
                status=500,
            )

        data = json.loads(request.body)

        support_type = data.get("support_type")  # one_time | monthly
        currency = (data.get("currency") or "usd").lower()
        amount = data.get("amount")

        if support_type not in {"one_time", "monthly"}:
            return JsonResponse({"error": "Invalid support_type"}, status=400)

        if currency not in {"pln", "eur", "usd"}:
            return JsonResponse({"error": "Invalid currency"}, status=400)

        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid amount"}, status=400)

        if amount_value <= 0:
            return JsonResponse({"error": "Amount must be greater than 0"}, status=400)

        min_amount = {"pln": 5.0, "eur": 1.0, "usd": 1.0}[currency]
        if amount_value < min_amount:
            return JsonResponse(
                {"error": f"Minimum amount is {min_amount:.0f} {currency.upper()}"},
                status=400,
            )

        unit_amount = int(round(amount_value * 100))
        session_mode = "payment" if support_type == "one_time" else "subscription"

        success_url = request.build_absolute_uri(reverse("frontend:contribute_success"))
        if "?" in success_url:
            success_url = f"{success_url}&session_id={{CHECKOUT_SESSION_ID}}"
        else:
            success_url = f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.build_absolute_uri(reverse("frontend:contribute"))

        if support_type == "monthly":
            line_items = [
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": unit_amount,
                        "recurring": {"interval": "month"},
                        "product_data": {"name": "Convertica Support (Monthly)"},
                    },
                    "quantity": 1,
                }
            ]
        else:
            line_items = [
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": unit_amount,
                        "product_data": {"name": "Convertica Support"},
                    },
                    "quantity": 1,
                }
            ]

        checkout_create_kwargs = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": session_mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": False,
            "billing_address_collection": "auto",
            "metadata": {
                "kind": "support",
                "support_type": support_type,
                "currency": currency,
                "amount": str(amount_value),
            },
        }
        if support_type == "monthly":
            checkout_create_kwargs["subscription_data"] = {
                "metadata": {"kind": "support", "support_type": "monthly"}
            }

        checkout_session = stripe.checkout.Session.create(**checkout_create_kwargs)

        return JsonResponse({"checkout_url": checkout_session.url})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe support checkout error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        logger.exception(f"Support checkout session error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@require_http_methods(["POST"])
def create_checkout_session(request):
    """Create Stripe checkout session for subscription."""
    try:
        if not bool(getattr(settings, "PAYMENTS_ENABLED", True)):
            return JsonResponse(
                {"error": "Payments are temporarily unavailable."},
                status=503,
            )
        _ensure_stripe_sdk_ready()
        data = json.loads(request.body)
        plan_slug = data.get("plan_slug")

        if not plan_slug:
            return JsonResponse({"error": "Plan slug is required"}, status=400)

        # Get plan directly by slug
        try:
            plan = SubscriptionPlan.objects.get(slug=plan_slug, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return JsonResponse({"error": "Plan not found"}, status=404)

        # Get user
        user = request.user

        # If user already has an active subscription, redirect to Billing Portal
        existing_subscription = (
            UserSubscription.objects.filter(user=user)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        has_blocking_subscription = False
        if existing_subscription:
            if existing_subscription.is_active():
                has_blocking_subscription = True
            else:
                # Treat past_due/unpaid/incomplete within the current period as managed via portal
                now = timezone.now()
                if (
                    existing_subscription.status in {"past_due", "unpaid", "incomplete"}
                    and existing_subscription.current_period_end
                    and existing_subscription.current_period_end > now
                ):
                    has_blocking_subscription = True

        if has_blocking_subscription:
            return_url = request.build_absolute_uri(
                reverse("users:manage_subscription")
            )
            portal_session = _create_billing_portal_session(user, return_url=return_url)
            if portal_session and getattr(portal_session, "url", None):
                return JsonResponse(
                    {
                        "error": "You already have an active subscription. Manage it in the billing portal.",
                        "portal_url": portal_session.url,
                    },
                    status=409,
                )
            return JsonResponse(
                {
                    "error": "You already have an active subscription. Please manage it from your account page.",
                    "manage_url": return_url,
                },
                status=409,
            )

        # Get or create Stripe customer
        customer_id = user.get_stripe_customer_id()

        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name() or user.email,
                metadata={"user_id": user.id},
                idempotency_key=f"convertica_customer_{user.id}",
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            user.save(update_fields=["stripe_customer_id"])

        # Ensure Stripe price exists AND matches the plan duration.
        # If a wrong price was previously created (e.g. monthly plan pointing to daily price),
        # recreate a correct price and update stripe_price_id.
        with transaction.atomic():
            locked_plan = (
                SubscriptionPlan.objects.select_for_update().filter(pk=plan.pk).first()
            )
            if locked_plan:
                plan = locked_plan

                expected_interval = (
                    "day"
                    if plan.duration_days == 1
                    else "month" if plan.duration_days == 30 else "year"
                )

                needs_new_price = not plan.stripe_price_id
                if plan.stripe_price_id:
                    try:
                        stripe_price = stripe.Price.retrieve(plan.stripe_price_id)
                        recurring = getattr(stripe_price, "recurring", None)
                        current_interval = getattr(recurring, "interval", None)
                        current_count = getattr(recurring, "interval_count", None)
                        current_amount = getattr(stripe_price, "unit_amount", None)
                        current_currency = getattr(stripe_price, "currency", None)
                        expected_amount = int(plan.price * 100)
                        expected_currency = plan.currency.lower()

                        if (
                            current_interval != expected_interval
                            or (current_count and int(current_count) != 1)
                            or (
                                current_amount is not None
                                and int(current_amount) != expected_amount
                            )
                            or (
                                current_currency
                                and str(current_currency).lower() != expected_currency
                            )
                        ):
                            needs_new_price = True
                    except Exception:
                        # If Stripe price retrieval fails, recreate the price.
                        needs_new_price = True

                if needs_new_price:
                    idempotency_key = (
                        f"convertica_price_{plan.id}_"
                        f"{int(plan.price * 100)}_"
                        f"{plan.currency.lower()}_"
                        f"{expected_interval}"
                    )
                    new_price = stripe.Price.create(
                        unit_amount=int(plan.price * 100),
                        currency=plan.currency.lower(),
                        recurring={
                            "interval": expected_interval,
                            "interval_count": 1,
                        },
                        product_data={
                            "name": plan.name,
                        },
                        metadata={"plan_id": plan.id},
                        idempotency_key=idempotency_key,
                    )
                    plan.stripe_price_id = new_price.id
                    plan.save(update_fields=["stripe_price_id"])

        # Create checkout session
        # Use subscription mode for all plans (including daily)
        success_url = request.build_absolute_uri(reverse("payments:payment_success"))
        if "?" in success_url:
            success_url = f"{success_url}&session_id={{CHECKOUT_SESSION_ID}}"
        else:
            success_url = f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.build_absolute_uri(reverse("payments:payment_cancel"))

        subscription_data = {
            "metadata": {
                "kind": "premium",
                "user_id": str(user.id),
                "plan_id": str(plan.id),
            }
        }

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user.id,
                "plan_id": plan.id,
                "payment_type": "subscription",
            },
            subscription_data=subscription_data,
            allow_promotion_codes=True,
            billing_address_collection="auto",
            customer_update={
                "address": "auto",
                "name": "auto",
            },
        )

        return JsonResponse(
            {"session_id": checkout_session.id, "checkout_url": checkout_session.url}
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        logger.exception(f"Checkout session error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
def payment_success(request):
    """Handle successful payment."""
    session_id = request.GET.get("session_id")

    if not session_id:
        return render(
            request, "payments/error.html", {"error": "No session ID provided"}
        )

    try:
        # Try to find payment in DB first (webhook may have already processed it)
        payment = (
            Payment.objects.filter(
                user=request.user, payment_id__icontains=session_id, status="completed"
            )
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )

        def _subscription_context():
            """Provide subscription period dates for the success template."""
            sub = (
                UserSubscription.objects.filter(user=request.user)
                .exclude(current_period_end__isnull=True)
                .order_by("-updated_at", "-created_at")
                .first()
            )
            if sub and (sub.current_period_start or sub.current_period_end):
                return sub

            # Fallback to user fields (populated by webhook/checkout completion)
            return {
                "current_period_start": getattr(
                    request.user, "subscription_start_date", None
                ),
                "current_period_end": getattr(
                    request.user, "subscription_end_date", None
                ),
            }

        if payment:
            # Payment already processed by webhook
            request.user.refresh_from_db()
            return render(
                request,
                "payments/success.html",
                {
                    "plan": payment.plan,
                    "payment_type": (
                        "one_time"
                        if payment.plan.duration_days == 1
                        else "subscription"
                    ),
                    "amount": payment.amount,
                    "subscription": _subscription_context(),
                },
            )

        # Check subscription
        subscription = (
            UserSubscription.objects.filter(user=request.user, status="active")
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )

        if subscription:
            request.user.refresh_from_db()
            return render(
                request,
                "payments/success.html",
                {
                    "plan": subscription.plan,
                    "payment_type": "subscription",
                    "subscription": subscription,
                },
            )

        # Fallback: retrieve from Stripe (webhook may not have processed yet)
        _ensure_stripe_sdk_ready()
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return render(
                request, "payments/error.html", {"error": "Payment was not successful"}
            )

        handle_checkout_session_completed(session)
        request.user.refresh_from_db()

        plan_id = session.metadata.get("plan_id")
        payment_type = session.metadata.get("payment_type", "subscription")

        plan = SubscriptionPlan.objects.get(id=plan_id)
        subscription = (
            UserSubscription.objects.filter(user=request.user)
            .exclude(current_period_end__isnull=True)
            .order_by("-updated_at", "-created_at")
            .first()
        )

        return render(
            request,
            "payments/success.html",
            {
                "plan": plan,
                "payment_type": payment_type,
                "subscription": subscription or _subscription_context(),
            },
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe success error: {e}")
        return render(
            request, "payments/error.html", {"error": "Payment verification failed"}
        )
    except Exception as e:
        logger.error(f"Payment success error: {e}")
        return render(
            request, "payments/error.html", {"error": "Internal server error"}
        )


@login_required
def payment_cancel(request):
    """Handle cancelled payment."""
    return render(request, "payments/cancel.html")


def _get_client_ip(request) -> str:
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _check_stripe_webhook_ip(request) -> bool:
    """Verify webhook request comes from Stripe IP addresses.

    Returns True if IP check passes or is disabled.
    """
    if not getattr(settings, "STRIPE_WEBHOOK_IP_WHITELIST_ENABLED", True):
        return True

    allowed_ips = getattr(settings, "STRIPE_WEBHOOK_IPS", [])
    if not allowed_ips:
        # No IPs configured, skip check
        return True

    client_ip = _get_client_ip(request)
    if client_ip in allowed_ips:
        return True

    logger.warning(
        "Stripe webhook from unauthorized IP",
        extra={
            "event": "stripe_webhook_ip_blocked",
            "client_ip": client_ip,
            "allowed_ips_count": len(allowed_ips),
        },
    )
    return False


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    # IP whitelist check (additional layer on top of signature verification)
    if not _check_stripe_webhook_ip(request):
        return HttpResponse("Forbidden", status=403)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        return HttpResponse("No signature", status=400)

    try:
        _ensure_stripe_sdk_ready()
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature error: {e}")
        return HttpResponse("Invalid signature", status=400)

    # DB-level idempotency: if event_id already exists, we already handled it.
    try:
        webhook_event = StripeWebhookEvent.objects.create(
            event_id=event.id,
            event_type=getattr(event, "type", ""),
            livemode=bool(getattr(event, "livemode", False)),
            processing=True,
        )
    except IntegrityError:
        return HttpResponse("OK")

    try:
        # Handle the event
        if event.type == "checkout.session.completed":
            session = event.data.object
            handle_checkout_session_completed(session)
        elif event.type == "checkout.session.expired":
            session = event.data.object
            handle_checkout_session_expired(session)
        elif event.type == "invoice.payment_succeeded":
            invoice = event.data.object
            handle_invoice_payment_succeeded(invoice)
        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            handle_invoice_payment_failed(invoice)
        elif (
            event.type == "customer.subscription.created"
            or event.type == "customer.subscription.updated"
        ):
            subscription = event.data.object
            handle_subscription_updated(subscription)
        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            handle_subscription_deleted(subscription)
        elif event.type == "charge.refunded":
            charge = event.data.object
            handle_charge_refunded(charge)
        elif event.type == "charge.dispute.created":
            dispute = event.data.object
            handle_charge_dispute_created(dispute)

        webhook_event.processing = False
        webhook_event.processed_at = timezone.now()
        webhook_event.last_error = ""
        webhook_event.save(update_fields=["processing", "processed_at", "last_error"])
        return HttpResponse("OK")
    except Exception as e:
        webhook_event.processing = False
        webhook_event.last_error = str(e)[:2000]
        webhook_event.save(update_fields=["processing", "last_error"])
        raise


def handle_checkout_session_completed(session):
    """Handle completed checkout session."""
    try:
        if (
            getattr(session, "metadata", None)
            and session.metadata.get("kind") == "support"
        ):
            logger.info("Support checkout completed")
            return

        user_id = session.metadata.get("user_id")
        plan_id = session.metadata.get("plan_id")
        payment_type = session.metadata.get("payment_type", "subscription")

        user = User.objects.get(id=user_id)
        plan = SubscriptionPlan.objects.get(id=plan_id)
        now = timezone.now()

        if payment_type == "one_time" and plan.duration_days == 1:
            payment_id = session.payment_intent or session.id
            payment, created = Payment.create_from_webhook(
                payment_id=payment_id,
                user=user,
                plan=plan,
                amount=plan.price,
                status="completed",
                payment_method="stripe",
                processed_at=now,
            )
            if not created and payment.status != "completed":
                payment.status = "completed"
                payment.processed_at = now
                payment._skip_subscription_sync = True
                payment.save(update_fields=["status", "processed_at"])
            return

        if not user.stripe_customer_id and getattr(session, "customer", None):
            user.stripe_customer_id = session.customer
            user.save(update_fields=["stripe_customer_id"])

        if getattr(session, "subscription", None):
            _ensure_stripe_sdk_ready()
            stripe_sub = stripe.Subscription.retrieve(session.subscription)
            stripe_status = getattr(stripe_sub, "status", "active") or "active"
            period_start = getattr(stripe_sub, "current_period_start", None)
            period_end = getattr(stripe_sub, "current_period_end", None)

            if not period_start or not period_end:
                items = _stripe_obj_get(stripe_sub, "items")
                data = _stripe_obj_get(items, "data") or []
                if data:
                    period_start = period_start or _stripe_obj_get(
                        data[0], "current_period_start"
                    )
                    period_end = period_end or _stripe_obj_get(
                        data[0], "current_period_end"
                    )
            cancel_at_period_end = bool(
                getattr(stripe_sub, "cancel_at_period_end", False)
            )

            # If Checkout is paid, treat entitlement as active even if Stripe still reports
            # a transient status (e.g. incomplete) at this exact moment.
            effective_status = stripe_status
            if getattr(
                session, "payment_status", None
            ) == "paid" and stripe_status not in {"active", "trialing"}:
                effective_status = "active"

            # Fallback period if Stripe hasn't populated it yet
            if not period_start or not period_end:
                now_ts = int(timezone.now().timestamp())
                period_start = period_start or now_ts
                period_end = period_end or int(
                    (
                        timezone.now() + timezone.timedelta(days=plan.duration_days)
                    ).timestamp()
                )

            # Daily Hero is intended to be a 1-day access pass (no auto-renew).
            # Stripe Checkout does not support subscription_data[cancel_at_period_end] at session creation,
            # so we set it after the subscription is created.
            if plan.duration_days == 1 and not cancel_at_period_end:
                try:
                    stripe.Subscription.modify(
                        session.subscription,
                        cancel_at_period_end=True,
                    )
                    cancel_at_period_end = True
                except Exception as e:
                    logger.warning(
                        "Failed to set cancel_at_period_end for daily subscription",
                        extra={
                            "event": "daily_cancel_at_period_end_failed",
                            "subscription_id": session.subscription,
                            "error": str(e)[:200],
                        },
                    )
                    # Still mark it locally so UI/entitlement behaves as 1-day access.
                    cancel_at_period_end = True

            defaults = {
                "plan": plan,
                "stripe_subscription_id": session.subscription,
                "stripe_customer_id": session.customer,
                "status": effective_status,
                "cancel_at_period_end": cancel_at_period_end,
            }
            if period_start:
                defaults["current_period_start"] = _dt_from_timestamp(period_start)
            if period_end:
                defaults["current_period_end"] = _dt_from_timestamp(period_end)
            UserSubscription.objects.update_or_create(user=user, defaults=defaults)

            _sync_user_from_subscription(
                user, effective_status, period_start, period_end
            )

            if getattr(session, "payment_status", None) == "paid":
                Payment.create_from_webhook(
                    payment_id=getattr(session, "id", None)
                    or getattr(session, "subscription", None),
                    user=user,
                    plan=plan,
                    amount=plan.price,
                    status="completed",
                    payment_method="stripe",
                    transaction_id=getattr(session, "subscription", None),
                    processed_at=now,
                )
            return

        # Update subscription (fallback)
        subscription, created = UserSubscription.objects.get_or_create(
            user=user,
            defaults={
                "plan": plan,
                "stripe_subscription_id": session.subscription,
                "stripe_customer_id": session.customer,
                "status": "active",
                "current_period_start": timezone.now(),
                "current_period_end": timezone.now()
                + timezone.timedelta(days=plan.duration_days),
                "cancel_at_period_end": bool(plan.duration_days == 1),
            },
        )

        if not created:
            subscription.status = "active"
            subscription.current_period_end = timezone.now() + timezone.timedelta(
                days=plan.duration_days
            )
            if plan.duration_days == 1:
                subscription.cancel_at_period_end = True
            subscription.save(
                update_fields=["status", "current_period_end", "cancel_at_period_end"]
            )

        user.subscription_start_date = subscription.current_period_start
        user.subscription_end_date = subscription.current_period_end
        user.is_premium = True
        user._subscription_changed = True
        user.save(
            update_fields=[
                "subscription_start_date",
                "subscription_end_date",
                "is_premium",
            ]
        )

        if getattr(session, "payment_status", None) == "paid":
            Payment.create_from_webhook(
                payment_id=getattr(session, "id", None)
                or getattr(session, "subscription", None),
                user=user,
                plan=plan,
                amount=plan.price,
                status="completed",
                payment_method="stripe",
                transaction_id=getattr(session, "subscription", None),
                processed_at=now,
            )

    except Exception as e:
        logger.error(f"Handle checkout session error: {e}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment."""
    try:
        subscription_id = getattr(invoice, "subscription", None)
        if not subscription_id:
            # Some invoice objects may not carry subscription at top-level.
            # Try to resolve it from invoice lines.
            try:
                lines = getattr(invoice, "lines", None)
                line_items = getattr(lines, "data", None) or []
                if line_items:
                    subscription_id = getattr(line_items[0], "subscription", None)
            except Exception:
                subscription_id = None

        if not subscription_id:
            # Manual invoices created from Stripe Dashboard are often not linked to a subscription.
            # Try to map the invoice to a user and a plan via customer + price.
            customer_id = getattr(invoice, "customer", None)
            plan = None
            try:
                lines = getattr(invoice, "lines", None)
                line_items = getattr(lines, "data", None) or []
                if line_items:
                    price_obj = getattr(line_items[0], "price", None)
                    price_id = getattr(price_obj, "id", None)
                    if price_id:
                        plan = SubscriptionPlan.objects.filter(
                            stripe_price_id=price_id
                        ).first()
            except Exception:
                plan = None

            user = None
            if customer_id:
                user = User.objects.filter(stripe_customer_id=customer_id).first()

            if not user or not plan:
                logger.info(
                    "Invoice payment succeeded without subscription_id (skipping)",
                    extra={
                        "event": "invoice_payment_succeeded_no_subscription",
                        "invoice_id": getattr(invoice, "id", None),
                        "billing_reason": getattr(invoice, "billing_reason", None),
                        "customer_id": customer_id,
                        "resolved_user": bool(user),
                        "resolved_plan": bool(plan),
                    },
                )
                return

            # Treat this as a manual premium purchase/renewal for the resolved plan.
            now = timezone.now()
            current_end = user.subscription_end_date or now
            if current_end < now:
                current_end = now
            new_end = current_end + timezone.timedelta(days=plan.duration_days)

            user.subscription_start_date = user.subscription_start_date or now
            user.subscription_end_date = new_end
            user.is_premium = True
            user._subscription_changed = True
            user.save(
                update_fields=[
                    "subscription_start_date",
                    "subscription_end_date",
                    "is_premium",
                ]
            )

            UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    "plan": plan,
                    "stripe_customer_id": customer_id,
                    "status": "active",
                    "current_period_start": now,
                    "current_period_end": new_end,
                },
            )

            payment_id = getattr(invoice, "id", None)
            if payment_id:
                Payment.create_from_webhook(
                    payment_id=payment_id,
                    user=user,
                    plan=plan,
                    amount=plan.price,
                    status="completed",
                    payment_method="stripe",
                    processed_at=now,
                )

            logger.info(
                "Manual invoice mapped to premium entitlement",
                extra={
                    "event": "manual_invoice_mapped",
                    "invoice_id": getattr(invoice, "id", None),
                    "customer_id": customer_id,
                    "user_id": getattr(user, "id", None),
                    "plan_id": getattr(plan, "id", None),
                },
            )
            return

        _ensure_stripe_sdk_ready()
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        if (
            getattr(stripe_subscription, "metadata", None)
            and stripe_subscription.metadata.get("kind") == "support"
        ):
            return

        subscription = UserSubscription.objects.select_related("user", "plan").get(
            stripe_subscription_id=subscription_id
        )

        # Update subscription period
        subscription.status = "active"
        subscription.current_period_start = _dt_from_timestamp(invoice.period_start)
        subscription.current_period_end = _dt_from_timestamp(invoice.period_end)
        subscription.save()

        _sync_user_from_subscription(
            subscription.user,
            "active",
            invoice.period_start,
            invoice.period_end,
        )

        payment_id = getattr(invoice, "payment_intent", None) or getattr(
            invoice, "id", None
        )
        if payment_id:
            payment, created = Payment.create_from_webhook(
                payment_id=payment_id,
                user=subscription.user,
                plan=subscription.plan,
                amount=subscription.plan.price,
                status="completed",
                payment_method="stripe",
                processed_at=timezone.now(),
            )
            if not created and payment.status != "completed":
                payment.status = "completed"
                payment.processed_at = timezone.now()
                payment._skip_subscription_sync = True
                payment.save(update_fields=["status", "processed_at"])

    except Exception as e:
        logger.error(f"Handle invoice payment succeeded error: {e}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment."""
    try:
        subscription_id = invoice.subscription
        if subscription_id:
            _ensure_stripe_sdk_ready()
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            if (
                getattr(stripe_subscription, "metadata", None)
                and stripe_subscription.metadata.get("kind") == "support"
            ):
                return
        subscription = UserSubscription.objects.select_related("user").get(
            stripe_subscription_id=subscription_id
        )

        subscription.status = "past_due"
        subscription.save()

        # Apply grace policy: keep premium for N days if configured, else cancel immediately.
        _sync_user_from_subscription(subscription.user, "past_due", None, None)

    except Exception as e:
        logger.error(f"Handle invoice payment failed error: {e}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion."""
    try:
        if (
            getattr(subscription, "metadata", None)
            and subscription.metadata.get("kind") == "support"
        ):
            return
        user_subscription = UserSubscription.objects.select_related("user").get(
            stripe_subscription_id=subscription.id
        )
        user_subscription.status = "canceled"
        user_subscription.save()

        # Cancel user subscription
        user_subscription.user.cancel_subscription()

    except Exception as e:
        logger.error(f"Handle subscription deleted error: {e}")
