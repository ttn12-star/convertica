# pylint: skip-file
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    OperationRun,
    Payment,
    StripeWebhookEvent,
    SubscriptionPlan,
    UserSubscription,
)

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with social account integration."""

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "subscription_status",
        "subscription_rank",
        "consecutive_days",
        "is_active",
        "is_staff",
        "date_joined",
        "social_accounts",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_premium",
        "date_joined",
        "socialaccount__provider",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Subscription",
            {
                "fields": (
                    "is_premium",
                    "subscription_start_date",
                    "subscription_end_date",
                    "consecutive_subscription_days",
                    "total_subscription_days",
                    "display_as_hero",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = (
        "consecutive_subscription_days",
        "total_subscription_days",
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )

    def subscription_status(self, obj):
        """Display subscription status with color coding."""
        if obj.is_premium:
            if obj.subscription_end_date and obj.subscription_end_date < timezone.now():
                return mark_safe(
                    '<span style="color: #ff6b6b; font-weight: bold;">EXPIRED</span>'
                )
            return mark_safe(
                '<span style="color: #51cf66; font-weight: normal;">Premium</span>'
            )
        return mark_safe('<span style="color: #868e96;">Free</span>')

    subscription_status.short_description = "Subscription"

    def subscription_rank(self, obj):
        """Display subscription rank with color."""
        rank = obj.get_subscription_rank()
        if rank:
            colors = {
                "Platinum": "#9775fa",
                "Gold": "#ffd43b",
                "Silver": "#868e96",
                "Bronze": "#ff922b",
            }
            color = colors.get(rank["name"], "#868e96")
            return mark_safe(
                f'<span style="color: {color}; font-weight: bold;">{rank["name"]}</span>'
            )
        return mark_safe('<span style="color: #868e96;">No rank</span>')

    subscription_rank.short_description = "Rank"

    def consecutive_days(self, obj):
        """Display consecutive subscription days."""
        days = obj.consecutive_subscription_days
        if days > 0:
            if days >= 365:
                return mark_safe(
                    f'<span style="color: #9775fa; font-weight: bold;">{days}</span>'
                )
            elif days >= 180:
                return mark_safe(
                    f'<span style="color: #ffd43b; font-weight: bold;">{days}</span>'
                )
            elif days >= 90:
                return mark_safe(
                    f'<span style="color: #868e96; font-weight: bold;">{days}</span>'
                )
            elif days >= 30:
                return mark_safe(
                    f'<span style="color: #ff922b; font-weight: bold;">{days}</span>'
                )
        return mark_safe(f'<span style="color: #868e96;">{days}</span>')

    consecutive_days.short_description = "Days"

    def social_accounts(self, obj):
        """Display connected social accounts with links."""
        social_accounts = obj.socialaccount_set.all()
        if not social_accounts:
            return mark_safe('<span style="color: #999;">No social accounts</span>')

        accounts_html = []
        for account in social_accounts:
            provider_name = account.get_provider().name
            url = reverse("admin:socialaccount_socialaccount_change", args=[account.id])
            accounts_html.append(
                f'<a href="{url}" style="color: #4285F4; text-decoration: none;">'
                f"{provider_name}</a>"
            )

        return mark_safe("<br>".join(accounts_html))

    social_accounts.short_description = "Social Accounts"

    def save_model(self, request, obj, form, change):
        """Override save_model to allow manual admin edits."""
        # Set flag to prevent auto-updating is_premium during admin edits
        obj._admin_manual_edit = True
        super().save_model(request, obj, form, change)
        # Clean up the flag after save
        if hasattr(obj, "_admin_manual_edit"):
            delattr(obj, "_admin_manual_edit")

    def get_queryset(self, request):
        """Optimize queryset with related objects."""
        return super().get_queryset(request).prefetch_related("socialaccount_set")


class SocialAccountInline(admin.TabularInline):
    """Inline social accounts for user admin."""

    model = SocialAccount
    extra = 0
    readonly_fields = ("provider", "uid", "extra_data", "date_joined")

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj):
        return False


class SocialAccountAdmin(admin.ModelAdmin):
    """Custom SocialAccount admin with user information."""

    list_display = (
        "user_email",
        "provider",
        "uid",
        "date_joined",
        "last_login",
    )
    list_filter = ("provider", "date_joined", "last_login")
    search_fields = ("user__email", "uid", "extra_data")
    readonly_fields = (
        "provider",
        "uid",
        "user",
        "extra_data",
        "date_joined",
        "last_login",
    )

    fieldsets = (
        ("Account Information", {"fields": ("user", "provider", "uid")}),
        ("OAuth Data", {"fields": ("extra_data",), "classes": ("collapse",)}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )

    def user_email(self, obj):
        """Display user email with link to user admin."""
        if obj.user:
            url = reverse("admin:users_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "-"

    user_email.short_description = "User Email"

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        """Optimize queries with user prefetch."""
        return super().get_queryset(request).select_related("user")


# Custom admin site configuration
class CustomAdminSite(admin.AdminSite):
    """Custom admin site with enhanced user management."""

    site_header = "Convertica Administration"
    site_title = "Convertica Admin"
    index_title = "Welcome to Convertica Admin Panel"

    def get_app_list(self, request, app_label=None):
        """Reorder apps to put Users first."""
        app_list = super().get_app_list(request, app_label)

        # Move Users app to the beginning
        users_app = next((app for app in app_list if app["app_label"] == "users"), None)
        if users_app:
            app_list.remove(users_app)
            app_list.insert(0, users_app)

        return app_list


# Create custom admin instance
custom_admin = CustomAdminSite(name="custom_admin")

# Register models with custom admin
custom_admin.register(User, UserAdmin)
custom_admin.register(SocialAccount, SocialAccountAdmin)

# Register with default admin (unregister first if needed)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)

# Unregister and register SocialAccount with default admin
try:
    admin.site.unregister(SocialAccount)
except admin.sites.NotRegistered:
    pass
admin.site.register(SocialAccount, SocialAccountAdmin)

# Add SocialAccount inline to User admin
UserAdmin.inlines = [SocialAccountInline]


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Admin for subscription plans."""

    list_display = (
        "name",
        "slug",
        "price",
        "currency",
        "duration_days",
        "is_active",
        "stripe_price_id",
    )
    list_filter = ("is_active", "currency", "duration_days")
    search_fields = ("name", "slug", "description")
    ordering = ("price",)

    fieldsets = (
        ("Basic Info", {"fields": ("name", "slug", "description", "is_active")}),
        ("Pricing", {"fields": ("price", "currency", "duration_days")}),
        (
            "Stripe Integration",
            {"fields": ("stripe_price_id",), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("stripe_price_id",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin for payments."""

    list_display = (
        "user_email",
        "plan_name",
        "amount",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at", "plan")
    search_fields = ("user__email", "payment_id", "transaction_id")
    ordering = ("-created_at",)

    fieldsets = (
        ("Payment Info", {"fields": ("user", "plan", "amount", "status")}),
        (
            "Payment Details",
            {"fields": ("payment_id", "payment_method", "transaction_id")},
        ),
        ("Timestamps", {"fields": ("processed_at", "created_at", "updated_at")}),
    )

    readonly_fields = ("payment_id", "created_at", "updated_at")

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def plan_name(self, obj):
        return obj.plan.name

    plan_name.short_description = "Plan"


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    """Admin for user subscriptions."""

    list_display = (
        "user_email",
        "plan_name",
        "status",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
    )
    list_filter = ("status", "cancel_at_period_end", "plan")
    search_fields = ("user__email", "stripe_subscription_id")
    ordering = ("-created_at",)

    fieldsets = (
        ("Subscription Info", {"fields": ("user", "plan", "status")}),
        (
            "Stripe Details",
            {"fields": ("stripe_subscription_id", "stripe_customer_id")},
        ),
        ("Period", {"fields": ("current_period_start", "current_period_end")}),
        ("Settings", {"fields": ("cancel_at_period_end",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = (
        "stripe_subscription_id",
        "stripe_customer_id",
        "created_at",
        "updated_at",
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def plan_name(self, obj):
        return obj.plan.name if obj.plan else "No plan"

    plan_name.short_description = "Plan"


@admin.register(OperationRun)
class OperationRunAdmin(admin.ModelAdmin):
    list_display = (
        "conversion_type",
        "status",
        "is_premium",
        "user_email",
        "created_at",
        "queued_at",
        "started_at",
        "finished_at",
        "duration_ms",
        "queue_wait_ms",
    )
    list_filter = ("conversion_type", "status", "is_premium", "created_at")
    search_fields = ("task_id", "request_id", "user__email", "conversion_type")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user",)

    def user_email(self, obj):
        return obj.user.email if obj.user else "Anonymous"

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "event_id",
        "livemode",
        "processing",
        "processed_at",
        "created_at",
    )
    list_filter = ("event_type", "livemode", "processing", "created_at")
    search_fields = ("event_id",)
    readonly_fields = ("created_at", "updated_at")
