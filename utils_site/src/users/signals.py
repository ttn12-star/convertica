"""Signals for user management."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when a new User is created."""
    if created:
        # Here you can create additional profile data if needed
        pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when User is saved."""
    # Here you can save additional profile data if needed
    pass
