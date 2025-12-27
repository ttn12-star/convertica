# pylint: skip-file
from django.urls import path

from . import social_views, views

app_name = "users"

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("register/", views.user_register, name="register"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.user_profile, name="profile"),
    path(
        "resend-confirmation-email/",
        views.resend_confirmation_email,
        name="resend_confirmation_email",
    ),
    path(
        "send-password-reset-email/",
        views.send_password_reset_email,
        name="send_password_reset_email",
    ),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
    path("account-status/", views.account_status, name="account_status"),
    path("manage-subscription/", views.manage_subscription, name="manage_subscription"),
    path("cancel-subscription/", views.cancel_subscription, name="cancel_subscription"),
    path("delete-account/", views.delete_account, name="delete_account"),
    path("toggle-hero-display/", views.toggle_hero_display, name="toggle_hero_display"),
    path("download-data/", views.download_data, name="download_data"),
    path(
        "google-direct/", social_views.google_direct_oauth, name="google_direct_oauth"
    ),
    path("auth-status/", social_views.auth_status, name="auth_status"),
]
