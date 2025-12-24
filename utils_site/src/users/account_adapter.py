"""
Custom allauth account adapter for email verification redirects.
"""

from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to handle email confirmation redirects."""

    def get_email_verification_redirect_url(self, email_address):
        """Redirect after email verification/confirmation."""
        user = getattr(email_address, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return reverse("users:profile")
        return reverse("users:login")
