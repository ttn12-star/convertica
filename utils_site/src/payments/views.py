import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription

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
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name() or user.email,
                metadata={"user_id": user.id},
            )
            customer_id = customer.id
            # Save customer ID to user
            user.stripe_customer_id = customer_id
            user.save(update_fields=["stripe_customer_id"])

        # Create or get Stripe price if not exists
        if not plan.stripe_price_id:
            stripe_price = stripe.Price.create(
                unit_amount=int(plan.price * 100),  # Convert to cents
                currency=plan.currency.lower(),
                recurring={
                    "interval": (
                        "day"
                        if plan.duration_days == 1
                        else "month" if plan.duration_days == 30 else "year"
                    ),
                    "interval_count": 1,
                },
                product_data={
                    "name": plan.name,
                    "description": plan.description or f"{plan.name} subscription",
                },
                metadata={"plan_id": plan.id},
            )
            plan.stripe_price_id = stripe_price.id
            plan.save(update_fields=["stripe_price_id"])

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
        # Retrieve session
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            # Get user and plan from metadata
            user_id = session.metadata.get("user_id")
            plan_id = session.metadata.get("plan_id")
            payment_type = session.metadata.get("payment_type", "subscription")

            user = User.objects.get(id=user_id)
            plan = SubscriptionPlan.objects.get(id=plan_id)

            # Create payment record
            payment = Payment.objects.create(
                user=user,
                plan=plan,
                amount=plan.price,
                status="completed",
                payment_id=session.payment_intent or session.id,
                payment_method="stripe",
                processed_at=timezone.now(),
            )

            # Handle different payment types
            if payment_type == "one_time" and plan.duration_days == 1:
                # One-time payment for Daily Hero - no subscription created
                user.activate_subscription(plan)

                return render(
                    request,
                    "payments/success.html",
                    {
                        "plan": plan,
                        "payment_type": "one_time",
                        "message": f"You now have premium access for {plan.duration_days} day!",
                    },
                )
            else:
                # Recurring subscription for monthly/yearly plans
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
                    # Update existing subscription
                    subscription.plan = plan
                    subscription.stripe_subscription_id = session.subscription
                    subscription.stripe_customer_id = session.customer
                    subscription.status = session.status or "active"
                    subscription.current_period_start = timezone.now()
                    subscription.current_period_end = (
                        timezone.now() + timezone.timedelta(days=plan.duration_days)
                    )
                    subscription.save()

                # Activate user's premium subscription
                user.activate_subscription(plan)

                return render(
                    request,
                    "payments/success.html",
                    {
                        "plan": plan,
                        "payment_type": "subscription",
                        "subscription": subscription,
                    },
                )
        else:
            return render(
                request, "payments/error.html", {"error": "Payment was not successful"}
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

    return HttpResponse("OK")


def handle_checkout_session_completed(session):
    """Handle completed checkout session."""
    try:
        user_id = session.metadata.get("user_id")
        plan_id = session.metadata.get("plan_id")

        user = User.objects.get(id=user_id)
        plan = SubscriptionPlan.objects.get(id=plan_id)

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

        # Activate user subscription
        user.activate_subscription(plan)

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

        # Activate user subscription
        subscription.user.activate_subscription(subscription.plan)

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
