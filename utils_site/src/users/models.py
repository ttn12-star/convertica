from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    # Legacy field - kept for backward compatibility
    is_premium = models.BooleanField(default=False, verbose_name=_("Is Premium"))
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

    username = models.CharField(max_length=150, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()  # <-- подключаем кастомный менеджер

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        app_label = "users"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """Override save to update subscription fields based on dates and clear cache."""
        # Auto-calculate subscription days when dates are set
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

        # Clear cache when subscription data changes
        if hasattr(self, "_subscription_changed"):
            cache.delete(f"user_subscription_status_{self.id}")

        super().save(*args, **kwargs)

    def is_subscription_active(self):
        """Check if user's subscription is currently active with Redis caching."""
        cache_key = f"user_subscription_status_{self.id}"
        cached_status = cache.get(cache_key)

        if cached_status is not None:
            return cached_status

        if not self.subscription_end_date:
            status = False
        else:
            status = timezone.now() <= self.subscription_end_date

        # Cache for 5 minutes
        cache.set(cache_key, status, 300)
        return status

    @property
    def subscription_status(self):
        """Get current subscription status."""
        if not self.is_premium or not self.subscription_end_date:
            return "expired"

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
                "badge_color": "bg-purple-600",
                "text_color": "text-white",
                "border_color": "border-purple-500",
                "gradient": "from-purple-600/70 to-indigo-600/70",
            }
        elif days >= 180:
            return {
                "name": "Gold",
                "color": "yellow",
                "badge_color": "bg-yellow-600",
                "text_color": "text-white",
                "border_color": "border-yellow-500",
                "gradient": "from-yellow-600/70 to-orange-600/70",
            }
        elif days >= 90:
            return {
                "name": "Silver",
                "color": "gray",
                "badge_color": "bg-gray-500",
                "text_color": "text-white",
                "border_color": "border-gray-400",
                "gradient": "from-gray-500/70 to-gray-600/70",
            }
        elif days >= 30:
            return {
                "name": "Bronze",
                "color": "orange",
                "badge_color": "bg-orange-600",
                "text_color": "text-white",
                "border_color": "border-orange-500",
                "gradient": "from-orange-600/70 to-amber-600/70",
            }
        else:
            return None

    def activate_subscription(self, plan):
        """Activate subscription for given plan."""
        from datetime import timedelta

        self.subscription_start_date = timezone.now()
        self.subscription_end_date = timezone.now() + timedelta(days=plan.duration_days)
        self.total_subscription_days += plan.duration_days
        self.consecutive_subscription_days += plan.duration_days
        self.is_premium = True
        self._subscription_changed = True
        self.save()

    def cancel_subscription(self):
        """Cancel subscription immediately."""
        self.subscription_end_date = timezone.now()
        self.consecutive_subscription_days = 0
        self._subscription_changed = True
        self.save()

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

        heroes = cls.objects.filter(display_as_hero=True, is_premium=True).order_by(
            "-consecutive_subscription_days"
        )

        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, heroes, 300)
        return heroes

    @classmethod
    def get_top_subscribers(cls, limit=10):
        """Get top premium subscribers by consecutive days with caching."""
        cache_key = f"top_subscribers_{limit}"
        cached_top = cache.get(cache_key)

        if cached_top is not None:
            return cached_top

        top = cls.objects.filter(display_as_hero=True, is_premium=True).order_by(
            "-consecutive_subscription_days"
        )[:limit]

        # Cache for 24 hours (86400 seconds)
        cache.set(cache_key, list(top), 86400)
        return top


class SubscriptionPlan(models.Model):
    """Subscription plan model with pricing."""

    PLAN_TYPES = [
        ("daily", _("Daily")),
        ("monthly", _("Monthly")),
        ("yearly", _("Yearly")),
    ]

    name = models.CharField(max_length=100, verbose_name=_("Plan Name"))
    plan_type = models.CharField(
        max_length=20, choices=PLAN_TYPES, verbose_name=_("Plan Type")
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price")
    )
    duration_days = models.IntegerField(verbose_name=_("Duration Days"))
    features = models.JSONField(default=list, verbose_name=_("Features"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - ${self.price}"


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
        """Override save to handle status changes and clear user cache."""
        is_new = self.pk is None
        old_status = None

        if not is_new:
            try:
                old_payment = Payment.objects.get(pk=self.pk)
                old_status = old_payment.status
            except Payment.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Clear user subscription cache when payment status changes to completed
        if (is_new and self.status == "completed") or (
            old_status != "completed" and self.status == "completed"
        ):
            cache.delete(f"user_subscription_status_{self.user.id}")
            # Activate subscription
            self.user.activate_subscription(self.plan)
        elif old_status == "completed" and self.status in ["refunded", "failed"]:
            cache.delete(f"user_subscription_status_{self.user.id}")
            # Cancel subscription
            self.user.cancel_subscription()

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
