from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "create-checkout-session/",
        views.create_checkout_session,
        name="create_checkout_session",
    ),
    path(
        "create-support-checkout-session/",
        views.create_support_checkout_session,
        name="create_support_checkout_session",
    ),
    path("success/", views.payment_success, name="payment_success"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),
    # Note: webhook is defined in root urls.py without i18n prefix
    # Stripe requires a fixed URL without language prefix
]
