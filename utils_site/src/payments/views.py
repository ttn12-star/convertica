import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
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


@login_required
@require_http_methods(["POST"])
def create_checkout_session(request):
    """Create Stripe checkout session for subscription."""
    try:
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

        # Create or get Stripe price if not exists
        if not plan.stripe_price_id:
            with transaction.atomic():
                locked_plan = (
                    SubscriptionPlan.objects.select_for_update()
                    .filter(pk=plan.pk)
                    .first()
                )
                if locked_plan and not locked_plan.stripe_price_id:
                    interval = (
                        "day"
                        if locked_plan.duration_days == 1
                        else "month" if locked_plan.duration_days == 30 else "year"
                    )
                    idempotency_key = (
                        f"convertica_price_{locked_plan.id}_"
                        f"{int(locked_plan.price * 100)}_"
                        f"{locked_plan.currency.lower()}_"
                        f"{interval}"
                    )
                    stripe_price = stripe.Price.create(
                        unit_amount=int(locked_plan.price * 100),
                        currency=locked_plan.currency.lower(),
                        recurring={
                            "interval": interval,
                            "interval_count": 1,
                        },
                        product_data={
                            "name": locked_plan.name,
                            "description": locked_plan.description
                            or f"{locked_plan.name} subscription",
                        },
                        metadata={"plan_id": locked_plan.id},
                        idempotency_key=idempotency_key,
                    )
                    locked_plan.stripe_price_id = stripe_price.id
                    locked_plan.save(update_fields=["stripe_price_id"])
                    plan = locked_plan
                elif locked_plan:
                    plan = locked_plan

        # Create checkout session
        # Use one-time payment for daily plan, subscription for others
        if plan.duration_days == 1:
            # One-time payment for Daily Hero
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": plan.stripe_price_id,
                        "quantity": 1,
                    }
                ],
                mode="payment",  # One-time payment
                success_url=request.build_absolute_uri(settings.STRIPE_SUCCESS_URL),
                cancel_url=request.build_absolute_uri(settings.STRIPE_CANCEL_URL),
                metadata={
                    "user_id": user.id,
                    "plan_id": plan.id,
                    "payment_type": "one_time",
                },
                allow_promotion_codes=True,
                billing_address_collection="auto",
                customer_update={
                    "address": "auto",
                    "name": "auto",
                },
            )
        else:
            # Recurring subscription for monthly/yearly plans
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": plan.stripe_price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",  # Recurring subscription
                success_url=request.build_absolute_uri(settings.STRIPE_SUCCESS_URL),
                cancel_url=request.build_absolute_uri(settings.STRIPE_CANCEL_URL),
                metadata={
                    "user_id": user.id,
                    "plan_id": plan.id,
                    "payment_type": "subscription",
                },
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
        logger.error(f"Checkout session error: {e}")
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
            .order_by("-created_at")
            .first()
        )

        if payment:
            # Payment already processed by webhook
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
                },
            )

        # Check subscription
        subscription = (
            UserSubscription.objects.filter(user=request.user, status="active")
            .order_by("-created_at")
            .first()
        )

        if subscription:
            return render(
                request,
                "payments/success.html",
                {
                    "plan": subscription.plan,
                    "payment_type": "subscription",
                },
            )

        # Fallback: retrieve from Stripe (webhook may not have processed yet)
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return render(
                request, "payments/error.html", {"error": "Payment was not successful"}
            )

        plan_id = session.metadata.get("plan_id")
        payment_type = session.metadata.get("payment_type", "subscription")

        plan = SubscriptionPlan.objects.get(id=plan_id)

        return render(
            request,
            "payments/success.html",
            {
                "plan": plan,
                "payment_type": payment_type,
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


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        return HttpResponse("No signature", status=400)

    try:
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
        elif event.type == "invoice.payment_succeeded":
            invoice = event.data.object
            handle_invoice_payment_succeeded(invoice)
        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            handle_invoice_payment_failed(invoice)
        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            handle_subscription_deleted(subscription)

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
        user_id = session.metadata.get("user_id")
        plan_id = session.metadata.get("plan_id")
        payment_type = session.metadata.get("payment_type", "subscription")

        user = User.objects.get(id=user_id)
        plan = SubscriptionPlan.objects.get(id=plan_id)

        if payment_type == "one_time" and plan.duration_days == 1:
            payment_id = session.payment_intent or session.id
            payment, created = Payment.objects.get_or_create(
                payment_id=payment_id,
                defaults={
                    "user": user,
                    "plan": plan,
                    "amount": plan.price,
                    "status": "completed",
                    "payment_method": "stripe",
                    "processed_at": timezone.now(),
                },
            )
            if not created and payment.status != "completed":
                payment.status = "completed"
                payment.processed_at = timezone.now()
                payment.save(update_fields=["status", "processed_at"])
            return

        # Update subscription
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
            },
        )

        if not created:
            subscription.status = "active"
            subscription.current_period_end = timezone.now() + timezone.timedelta(
                days=plan.duration_days
            )
            subscription.save()

    except Exception as e:
        logger.error(f"Handle checkout session error: {e}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment."""
    try:
        subscription_id = invoice.subscription
        subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription_id
        )

        # Update subscription period
        subscription.status = "active"
        subscription.current_period_start = timezone.fromtimestamp(invoice.period_start)
        subscription.current_period_end = timezone.fromtimestamp(invoice.period_end)
        subscription.save()

        payment_id = getattr(invoice, "payment_intent", None) or getattr(
            invoice, "id", None
        )
        if payment_id:
            payment, created = Payment.objects.get_or_create(
                payment_id=payment_id,
                defaults={
                    "user": subscription.user,
                    "plan": subscription.plan,
                    "amount": subscription.plan.price,
                    "status": "completed",
                    "payment_method": "stripe",
                    "processed_at": timezone.now(),
                },
            )
            if not created and payment.status != "completed":
                payment.status = "completed"
                payment.processed_at = timezone.now()
                payment.save(update_fields=["status", "processed_at"])

    except Exception as e:
        logger.error(f"Handle invoice payment succeeded error: {e}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment."""
    try:
        subscription_id = invoice.subscription
        subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription_id
        )

        subscription.status = "past_due"
        subscription.save()

    except Exception as e:
        logger.error(f"Handle invoice payment failed error: {e}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion."""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription.id
        )
        user_subscription.status = "canceled"
        user_subscription.save()

        # Cancel user subscription
        user_subscription.user.cancel_subscription()

    except Exception as e:
        logger.error(f"Handle subscription deleted error: {e}")
