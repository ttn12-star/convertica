"""User models for authentication."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom User model with additional fields."""

    email = models.EmailField(_("email address"), unique=True)
    is_premium = models.BooleanField(default=False, verbose_name=_("Is Premium"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    username = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        app_label = "users"

    def __str__(self):
        return self.email
