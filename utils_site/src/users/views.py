# pylint: skip-file
import json

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from .forms import CustomUserCreationForm, LoginForm
from .models import Payment


def user_login(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd["email"],  # Using email as username
                password=cd["password"],
            )
            if user is not None:
                if user.is_active:
                    from allauth.account.models import EmailAddress

                    if not EmailAddress.objects.filter(
                        user=user,
                        email=user.email,
                        verified=True,
                    ).exists():
                        return render(
                            request,
                            "users/login.html",
                            {
                                "form": form,
                                "error": _(
                                    "Please verify your email address before signing in."
                                ),
                            },
                        )
                    auth_login(request, user)
                    return redirect("users:profile")
                else:
                    return render(
                        request,
                        "users/login.html",
                        {"form": form, "error": _("Account is disabled")},
                    )
            else:
                return render(
                    request,
                    "users/login.html",
                    {"form": form, "error": _("Invalid email or password")},
                )
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def user_register(request):
    """Handle user registration with email verification."""
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Send email verification
            from allauth.account.models import EmailAddress
            from allauth.account.utils import send_email_confirmation

            # Create EmailAddress object for the user
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"primary": True, "verified": False},
            )

            # Send verification email
            send_email_confirmation(request, user, signup=True)

            # Show success message and redirect to login
            messages.success(
                request,
                _(
                    "Registration successful! Please check your email to verify your account before logging in."
                ),
            )
            return redirect("users:login")
    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form})


def user_logout(request):
    """Handle user logout with complete session cleanup."""
    # Clear all session data
    request.session.flush()

    # Perform Django logout
    auth_logout(request)

    # Clear authentication cookies only (keep language preference)
    response = redirect("users:login")
    response.delete_cookie("sessionid")

    # Add success message

    messages.success(request, _("You have been successfully logged out."))

    return response


@login_required
def user_profile(request):
    """Display user profile."""
    from allauth.account.models import EmailAddress

    # Check if email is verified
    email_verified = EmailAddress.objects.filter(
        user=request.user, email=request.user.email, verified=True
    ).exists()

    # Calculate days since registration for unverified accounts
    days_since_registration = None
    if not email_verified:
        from django.utils import timezone

        days_since_registration = (timezone.now() - request.user.date_joined).days

    context = {
        "user": request.user,
        "email_verified": email_verified,
        "days_since_registration": days_since_registration,
        "days_until_deletion": (
            max(0, 30 - days_since_registration)
            if days_since_registration is not None
            else None
        ),
    }

    return render(request, "users/profile.html", context)


@login_required
@require_POST
def resend_confirmation_email(request):
    from allauth.account.models import EmailAddress
    from allauth.account.utils import send_email_confirmation

    if EmailAddress.objects.filter(
        user=request.user,
        email=request.user.email,
        verified=True,
    ).exists():
        messages.info(request, _("Your email is already verified."))
        return redirect("users:profile")

    EmailAddress.objects.get_or_create(
        user=request.user,
        email=request.user.email,
        defaults={"primary": True, "verified": False},
    )

    send_email_confirmation(request, request.user, signup=False)
    return redirect("users:profile")


@login_required
@require_POST
def send_password_reset_email(request):
    from allauth.account.forms import ResetPasswordForm

    form = ResetPasswordForm(data={"email": request.user.email})
    if form.is_valid():
        form.save(request)
        messages.success(
            request,
            _("Password reset email sent. Please check your inbox and spam folder."),
        )
    else:
        messages.error(request, _("Unable to send password reset email."))

    return redirect("users:profile")


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update user profile."""

    fields = ["username", "first_name", "last_name"]
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile")
    success_message = _("Profile updated successfully!")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Profile")
        return context

    def form_valid(self, form):
        # Handle display_as_hero checkbox separately since it's not in form fields
        display_as_hero = self.request.POST.get("display_as_hero") == "on"
        self.request.user.display_as_hero = display_as_hero
        self.request.user.save()

        return super().form_valid(form)


@login_required
def account_status(request):
    """Display account status and subscription information."""
    # Use cached payment history
    payments = Payment.get_user_payment_history(request.user.id)
    return render(
        request,
        "users/account_status.html",
        {"user": request.user, "payments": payments},
    )


@login_required
def manage_subscription(request):
    """Display subscription management page."""
    # Use cached payment history
    payments = Payment.get_user_payment_history(request.user.id)
    return render(
        request,
        "users/manage_subscription.html",
        {"user": request.user, "payments": payments},
    )


@login_required
@require_POST
def cancel_subscription(request):
    """Cancel user's subscription."""
    user = request.user

    if not user.is_subscription_active():
        return JsonResponse(
            {"success": False, "error": _("No active subscription to cancel")}
        )

    try:
        # Get user's Stripe subscription
        from src.users.models import UserSubscription

        user_subscription = UserSubscription.objects.filter(user=user).first()

        if user_subscription and user_subscription.stripe_subscription_id:
            # Cancel subscription in Stripe
            import stripe
            import stripe.apps
            from django.conf import settings

            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Cancel at period end (immediate=False) or immediately (immediate=True)
            stripe.Subscription.delete(user_subscription.stripe_subscription_id)

        # Cancel local subscription
        user.cancel_subscription()

        return JsonResponse(
            {"success": True, "message": _("Subscription cancelled successfully")}
        )

    except Exception:
        return JsonResponse(
            {"success": False, "error": _("Failed to cancel subscription")}
        )


@login_required
@require_POST
def delete_account(request):
    """Delete user account with GDPR compliance."""
    user = request.user

    try:
        # Log out user first
        auth_logout(request)

        # Delete user (this will cascade delete related data)
        user.delete()

        return JsonResponse(
            {"success": True, "message": _("Account deleted successfully")}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def toggle_hero_display(request):
    """Toggle user's display in Heroes Hall."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": _("Method not allowed")})

    try:
        data = json.loads(request.body)
        display_as_hero = data.get("display_as_hero", False)

        # Update user's display preference
        request.user.display_as_hero = display_as_hero
        request.user.save(update_fields=["display_as_hero"])

        # Clear both heroes and top_subscribers caches to refresh the lists
        from django.core.cache import cache

        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")

        return JsonResponse(
            {
                "success": True,
                "display_as_hero": display_as_hero,
                "message": _("Hero display updated successfully"),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": _("Invalid JSON")}, status=400)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def download_data(request):
    """Download user data for GDPR compliance."""
    user = request.user

    # Get user rank if premium
    rank_info = None
    if user.is_premium:
        rank = user.get_subscription_rank()
        if rank:
            rank_info = {
                "name": rank.get("name"),
                "color": rank.get("color"),
                "badge_color": rank.get("badge_color"),
                "text_color": rank.get("text_color"),
                "border_color": rank.get("border_color"),
                "gradient": rank.get("gradient"),
            }

    # Collect user data
    data = {
        "_metadata": {
            "generated_at": timezone.now().isoformat(),
            "generated_by": "Convertica PDF Tools",
            "version": "1.0",
            "description": "Complete user data export for GDPR compliance",
        },
        "user_profile": {
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_premium": user.is_premium,
            "subscription_status": user.subscription_status,
            "subscription_start_date": (
                user.subscription_start_date.isoformat()
                if user.subscription_start_date
                else None
            ),
            "subscription_end_date": (
                user.subscription_end_date.isoformat()
                if user.subscription_end_date
                else None
            ),
            "total_subscription_days": user.total_subscription_days,
            "consecutive_subscription_days": user.consecutive_subscription_days,
            "display_as_hero": getattr(user, "display_as_hero", False),
            "rank": rank_info,
        },
        "subscription_summary": {
            "current_plan": "Premium" if user.is_premium else "Free",
            "active_subscription": user.is_subscription_active(),
            "subscription_duration_days": user.total_subscription_days,
            "current_streak_days": user.consecutive_subscription_days,
            "hero_status": (
                "Displayed in Heroes Hall"
                if getattr(user, "display_as_hero", False) and user.is_premium
                else "Not displayed"
            ),
        },
        "payment_history": [],
        "statistics": {
            "total_payments": 0,
            "total_amount": "0.00",
            "subscription_renewals": 0,
            "first_payment_date": None,
            "last_payment_date": None,
        },
    }

    # Add payment history
    payments = Payment.objects.filter(user=user).order_by("created_at")
    total_amount = 0
    renewals = 0

    for i, payment in enumerate(payments):
        payment_data = {
            "payment_id": payment.payment_id,
            "plan": payment.plan.name,
            "plan_type": payment.plan.plan_type,
            "amount": str(payment.amount),
            "currency": getattr(payment, "currency", "USD"),
            "status": payment.status,
            "created_at": payment.created_at.isoformat(),
            "payment_method": getattr(payment, "payment_method", "Unknown"),
            "is_renewal": i > 0,  # First payment is not a renewal
        }

        data["payment_history"].append(payment_data)
        total_amount += float(payment.amount)
        if i > 0:
            renewals += 1

    # Update statistics
    data["statistics"]["total_payments"] = len(payments)
    data["statistics"]["total_amount"] = f"{total_amount:.2f}"
    data["statistics"]["subscription_renewals"] = renewals

    if payments:
        data["statistics"][
            "first_payment_date"
        ] = payments.first().created_at.isoformat()
        data["statistics"]["last_payment_date"] = payments.last().created_at.isoformat()

    response = JsonResponse(
        data, json_dumps_params={"indent": 2, "ensure_ascii": False}
    )
    response["Content-Disposition"] = (
        f'attachment; filename="convertica_data_{user.username}_{timezone.now().strftime("%Y%m%d")}.json"'
    )
    response["Content-Type"] = "application/json; charset=utf-8"
    return response
