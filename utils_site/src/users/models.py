from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    # Legacy field - kept for backward compatibility
    is_premium = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Is Premium")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    # Subscription tracking fields
    subscription_start_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Subscription Start Date")
    )
    subscription_end_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Subscription End Date")
    )
    total_subscription_days = models.IntegerField(
        default=0, verbose_name=_("Total Subscription Days")
    )
    consecutive_subscription_days = models.IntegerField(
        default=0, verbose_name=_("Consecutive Subscription Days")
    )

    # Hero display settings
    display_as_hero = models.BooleanField(
        default=False, verbose_name=_("Display as Hero")
    )

    # Stripe integration
    stripe_customer_id = models.CharField(
        max_length=100, blank=True, null=True, editable=False
    )

    username = models.CharField(max_length=150, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscription_changed = False

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        app_label = "users"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """Override save to update subscription fields based on dates and clear cache."""
        # Skip auto-calculation if explicitly disabled (e.g., during cancellation)
        skip_days_calculation = getattr(self, "_skip_days_calculation", False)

        if not skip_days_calculation:
            # Auto-calculate subscription days when dates are set
            self._calculate_subscription_days()

        # Clear cache when subscription data changes (must happen BEFORE is_subscription_active())
        if getattr(self, "_subscription_changed", False):
            cache.delete(f"user_subscription_status_{self.id}")

        super().save(*args, **kwargs)

    def _calculate_subscription_days(self):
        """Calculate total and consecutive subscription days based on dates.

        This is the single source of truth for subscription day calculations.
        Called automatically in save() unless _skip_days_calculation is set.
        """
        if self.subscription_start_date and self.subscription_end_date:
            if self.subscription_end_date > self.subscription_start_date:
                # Calculate total days between start and end dates
                self.total_subscription_days = (
                    self.subscription_end_date - self.subscription_start_date
                ).days + 1

                # Calculate consecutive days from start date to today or end date
                today = timezone.now().date()
                if self.subscription_end_date.date() >= today:
                    # Active subscription - count from start to today
                    self.consecutive_subscription_days = (
                        today - self.subscription_start_date.date()
                    ).days + 1
                else:
                    # Expired subscription - count from start to end
                    self.consecutive_subscription_days = (
                        self.subscription_end_date.date()
                        - self.subscription_start_date.date()
                    ).days + 1
            else:
                # End date is before start date
                self.total_subscription_days = 0
                self.consecutive_subscription_days = 0
        else:
            # Missing dates
            self.total_subscription_days = 0
            self.consecutive_subscription_days = 0

        # Only auto-update is_premium if subscription_end_date is set
        # Allow manual override when editing via admin
        if self.subscription_end_date and not hasattr(self, "_admin_manual_edit"):
            self.is_premium = self.is_subscription_active()

    def is_subscription_active(self):
        """Check if user's subscription is currently active with Redis caching."""
        cache_key = f"user_subscription_status_{self.id}"
        cached_status = cache.get(cache_key)

        if cached_status is not None:
            return cached_status

        if not self.subscription_end_date:
            # Legacy/manual premium without an end date should be treated as active.
            status = bool(self.is_premium)
        else:
            status = timezone.now() <= self.subscription_end_date

        # Cache for 5 minutes
        cache.set(cache_key, status, 300)
        return status

    @property
    def is_premium_active(self) -> bool:
        """True only when the user is premium AND the subscription is currently active."""
        return bool(self.is_premium and self.is_subscription_active())

    @property
    def subscription_status(self):
        """Get current subscription status."""
        if not self.is_premium:
            return "expired"

        if not self.subscription_end_date:
            return "active"

        if self.subscription_end_date < timezone.now():
            return "expired"

        return "active"

    def get_subscription_rank(self):
        """Get user's subscription rank based on consecutive days."""
        days = self.consecutive_subscription_days

        if days >= 365:
            return {
                "name": "Platinum",
                "color": "purple",
                "icon": "sparkles",
                "badge_color": "bg-gradient-to-r from-fuchsia-600 to-indigo-600",
                "text_color": "text-white",
                "border_color": "border-fuchsia-500",
                "gradient": "from-fuchsia-600/70 to-indigo-600/70",
            }
        elif days >= 180:
            return {
                "name": "Gold",
                "color": "yellow",
                "icon": "crown",
                "badge_color": "bg-yellow-600",
                "text_color": "text-white",
                "border_color": "border-yellow-500",
                "gradient": "from-yellow-600/70 to-orange-600/70",
            }
        elif days >= 90:
            return {
                "name": "Silver",
                "color": "gray",
                "icon": "medal",
                "badge_color": "bg-gray-500",
                "text_color": "text-white",
                "border_color": "border-gray-400",
                "gradient": "from-gray-500/70 to-gray-600/70",
            }
        elif days >= 30:
            return {
                "name": "Bronze",
                "color": "orange",
                "icon": "shield",
                "badge_color": "bg-orange-600",
                "text_color": "text-white",
                "border_color": "border-orange-500",
                "gradient": "from-orange-600/70 to-amber-600/70",
            }
        else:
            # Default rank for all premium users (< 30 days)
            return {
                "name": "Hero",
                "color": "blue",
                "icon": "shield",
                "badge_color": "bg-blue-600",
                "text_color": "text-white",
                "border_color": "border-blue-500",
                "gradient": "from-blue-600/70 to-cyan-600/70",
            }

    def activate_subscription(self, plan, extend_if_active=True):
        """Activate or extend subscription for given plan.

        Args:
            plan: SubscriptionPlan instance
            extend_if_active: If True and subscription is already active,
                              extend it instead of resetting dates.
                              If False, only activate if not already active.
        """
        from datetime import timedelta

        now = timezone.now()

        # Check if subscription is currently active
        is_currently_active = (
            self.is_premium
            and self.subscription_end_date
            and self.subscription_end_date > now
        )

        if is_currently_active:
            if not extend_if_active:
                # Already active and we don't want to extend - skip
                return

            # Extend existing subscription from current end date
            self.subscription_end_date = self.subscription_end_date + timedelta(
                days=plan.duration_days
            )
            self.total_subscription_days += plan.duration_days
            # Don't reset consecutive_subscription_days - it's calculated in save()
        else:
            # New subscription or expired - set fresh start date
            self.subscription_start_date = now
            self.subscription_end_date = now + timedelta(days=plan.duration_days)
            self.total_subscription_days += plan.duration_days
            # consecutive_subscription_days will be calculated in save()

        self.is_premium = True
        self._subscription_changed = True
        self.save()

    def get_stripe_customer_id(self):
        """Get Stripe customer ID."""
        return self.stripe_customer_id

    def cancel_subscription(self):
        """Cancel subscription immediately and reset streak."""
        self.subscription_end_date = timezone.now()
        self.consecutive_subscription_days = 0  # Reset streak on cancellation
        self._subscription_changed = True
        self._skip_days_calculation = True  # Don't recalculate, keep 0
        self.save()
        # Clean up flag
        self._skip_days_calculation = False

    def is_hero(self):
        """Check if user qualifies as hero (premium user with display enabled)."""
        return self.is_premium and self.display_as_hero

    @classmethod
    def get_heroes(cls):
        """Get all premium users with display enabled for scrolling."""
        cache_key = "site_heroes"
        cached_heroes = cache.get(cache_key)

        if cached_heroes is not None:
            return cached_heroes

        now = timezone.now()
        heroes = cls.objects.filter(
            display_as_hero=True,
            subscription_end_date__isnull=False,
            subscription_end_date__gte=now,
        ).order_by("-consecutive_subscription_days")

        # Cache for 1 minute to ensure heroes disappear quickly after subscription expiry
        heroes_list = list(heroes)
        cache.set(cache_key, heroes_list, 60)
        return heroes_list

    @classmethod
    def get_top_subscribers(cls, limit=10):
        """Get top premium subscribers by consecutive days with caching."""
        cache_key = f"top_subscribers_{limit}"
        cached_top = cache.get(cache_key)

        if cached_top is not None:
            return cached_top

        now = timezone.now()
        top = cls.objects.filter(
            display_as_hero=True,
            subscription_end_date__isnull=False,
            subscription_end_date__gte=now,
        ).order_by("-consecutive_subscription_days")[:limit]

        # Cache for 5 minutes
        cache.set(cache_key, list(top), 300)
        return top


class SubscriptionPlan(models.Model):
    """Subscription plans for Stripe integration."""

    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    duration_days = models.IntegerField()
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - ${self.price}/{self.get_duration_display()}"

    def get_duration_display(self):
        if self.duration_days == 1:
            return "day"
        elif self.duration_days == 30:
            return "month"
        elif self.duration_days == 365:
            return "year"
        return f"{self.duration_days} days"


class RuntimeSetting(models.Model):
    """Admin-configurable runtime setting override (non-secret only)."""

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = _("Runtime Setting")
        verbose_name_plural = _("Runtime Settings")

    def __str__(self):
        return self.key

    def clean(self):
        normalized_key = (self.key or "").strip().upper()
        if not normalized_key:
            raise ValidationError({"key": _("Setting key cannot be empty.")})

        from .runtime_settings import is_sensitive_setting_key

        if is_sensitive_setting_key(normalized_key):
            raise ValidationError(
                {
                    "key": _(
                        "This setting key is considered secret and cannot be configured from admin."
                    )
                }
            )

        self.key = normalized_key

    def save(self, *args, **kwargs):
        from django.db import transaction

        self.full_clean()
        result = super().save(*args, **kwargs)

        from .runtime_settings import refresh_runtime_settings

        transaction.on_commit(refresh_runtime_settings)
        return result

    def delete(self, *args, **kwargs):
        from django.db import transaction

        result = super().delete(*args, **kwargs)

        from .runtime_settings import refresh_runtime_settings

        transaction.on_commit(refresh_runtime_settings)
        return result


class Payment(models.Model):
    """Payment model for tracking user payments."""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
        ("refunded", _("Refunded")),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.CASCADE, verbose_name=_("Plan")
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Amount")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name=_("Status"),
    )
    payment_id = models.CharField(
        max_length=100, unique=True, verbose_name=_("Payment ID")
    )
    # Additional fields for better tracking
    payment_method = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Payment Method")
    )
    transaction_id = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Transaction ID")
    )
    processed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Processed At")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["payment_id"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} - ${self.amount}"

    def save(self, *args, **kwargs):
        """Override save to handle status changes and clear user cache.

        Set self._skip_subscription_sync = True before saving if the subscription
        was already activated by webhook (to avoid double activation).
        """
        is_new = self.pk is None
        old_status = None
        skip_sync = getattr(self, "_skip_subscription_sync", False)

        if not is_new:
            try:
                old_payment = Payment.objects.get(pk=self.pk)
                old_status = old_payment.status
            except Payment.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Skip subscription sync if flag is set (webhook already handled it)
        if skip_sync:
            return

        # Clear user subscription cache when payment status changes to completed
        if (is_new and self.status == "completed") or (
            old_status != "completed" and self.status == "completed"
        ):
            cache.delete(f"user_subscription_status_{self.user.id}")
            # Activate subscription (extend_if_active=False to avoid overwriting
            # dates that were already set by webhook)
            self.user.activate_subscription(self.plan, extend_if_active=False)
        elif old_status == "completed" and self.status in ["refunded", "failed"]:
            cache.delete(f"user_subscription_status_{self.user.id}")
            # Cancel subscription
            self.user.cancel_subscription()

    @classmethod
    def create_from_webhook(cls, payment_id, user, plan, amount, **extra_fields):
        """Create Payment from webhook without triggering subscription activation.

        Use this when the subscription was already activated by the webhook handler
        to avoid double activation.

        Args:
            payment_id: Unique payment identifier
            user: User instance
            plan: SubscriptionPlan instance
            amount: Payment amount
            **extra_fields: Additional fields (status, payment_method, etc.)

        Returns:
            Tuple of (Payment, created) similar to get_or_create
        """
        try:
            payment = cls.objects.get(payment_id=payment_id)
            return payment, False
        except cls.DoesNotExist:
            payment = cls(
                payment_id=payment_id,
                user=user,
                plan=plan,
                amount=amount,
                **extra_fields,
            )
            payment._skip_subscription_sync = True
            payment.save()
            return payment, True

    @classmethod
    def get_user_payment_history(cls, user_id, limit=10):
        """Get cached user payment history."""
        cache_key = f"user_payment_history_{user_id}"
        cached_history = cache.get(cache_key)

        if cached_history is not None:
            return cached_history

        history = cls.objects.filter(user_id=user_id).order_by("-created_at")[:limit]

        # Cache for 10 minutes
        cache.set(cache_key, list(history), 600)
        return history


class StripeWebhookEvent(models.Model):
    """Stripe webhook event log for idempotent processing."""

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100, blank=True)
    livemode = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["processed_at"]),
        ]

    def __str__(self):
        return f"{self.event_type or 'stripe_event'} - {self.event_id}"


class OperationRun(models.Model):
    """Lightweight operational analytics for conversions and PDF tools."""

    STATUS_CHOICES = [
        ("started", "started"),
        ("queued", "queued"),
        ("running", "running"),
        ("success", "success"),
        ("error", "error"),
        ("cancel_requested", "cancel_requested"),
        ("cancelled", "cancelled"),
        ("abandoned", "abandoned"),
    ]

    conversion_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="started")

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operation_runs",
    )
    is_premium = models.BooleanField(default=False)

    request_id = models.CharField(max_length=64, blank=True)
    task_id = models.CharField(max_length=64, blank=True)

    input_size = models.BigIntegerField(null=True, blank=True)
    output_size = models.BigIntegerField(null=True, blank=True)

    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    duration_ms = models.IntegerField(null=True, blank=True)
    queue_wait_ms = models.IntegerField(null=True, blank=True)

    error_type = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)

    remote_addr = models.CharField(max_length=64, blank=True)
    user_agent = models.TextField(blank=True)
    path = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversion_type", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["task_id"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["is_premium", "conversion_type", "-created_at"]),
            # Composite indexes for analytics
            models.Index(fields=["user", "status", "-created_at"]),  # User dashboard
            models.Index(
                fields=["is_premium", "status", "-created_at"]
            ),  # Premium analytics
            models.Index(
                fields=["conversion_type", "status", "-created_at"]
            ),  # Conversion analytics
        ]

    def __str__(self):
        return f"{self.conversion_type} ({self.status})"


class UserSubscription(models.Model):
    """User subscription tracking."""

    user = models.OneToOneField(
        "User", on_delete=models.CASCADE, related_name="stripe_subscription"
    )
    plan = models.ForeignKey("SubscriptionPlan", on_delete=models.SET_NULL, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="incomplete")
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["stripe_subscription_id"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"

    def is_active(self):
        """Check if subscription is active."""
        return (
            self.status in ["active", "trialing"]
            and self.current_period_end
            and self.current_period_end > timezone.now()
        )

    @property
    def will_cancel(self):
        """Check if subscription will cancel at period end."""
        return self.cancel_at_period_end and self.is_active()
