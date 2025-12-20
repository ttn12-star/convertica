# pylint: skip-file
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with social account integration."""

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "date_joined",
        "social_accounts",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "socialaccount__provider",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
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

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )

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

    def get_queryset(self, request):
        """Optimize queries with social account prefetch."""
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


# SocialAccount is already registered by django-allauth
# We need to unregister it first before registering our custom admin
from django.contrib.admin import site

# Unregister the default SocialAccount admin if it exists
try:
    site.unregister(SocialAccount)
except admin.sites.NotRegistered:
    pass


@admin.register(SocialAccount)
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

# Add SocialAccount inline to User admin
UserAdmin.inlines = [SocialAccountInline]
