from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "create-checkout/",
        views.create_checkout_session,
        name="create_checkout_session",
    ),
    path("success/", views.payment_success, name="payment_success"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),
    # Webhook is registered in root urls.py without i18n prefix.
]
