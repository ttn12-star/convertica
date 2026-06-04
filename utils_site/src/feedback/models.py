"""Per-tool user feedback (1-5 stars + optional comment)."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from src.users.models import OperationRun


class ToolRating(models.Model):
    """A single 1-5 star rating (+ optional comment) for one tool operation."""

    tool_slug = models.CharField(max_length=80, db_index=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1000, blank=True)

    operation_run = models.ForeignKey(
        OperationRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ratings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tool_ratings",
    )
    session_key = models.CharField(max_length=40, blank=True)
    lang = models.CharField(max_length=8, blank=True)

    # Reserved for Stage 2 (public display + moderation). Unused in v1.
    is_approved = models.BooleanField(default=False)
    is_spam = models.BooleanField(default=False)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operation_run"], name="uniq_rating_per_operation"
            )
        ]
        indexes = [
            models.Index(fields=["tool_slug", "-created_at"]),
            models.Index(fields=["rating", "-created_at"]),
            models.Index(fields=["is_approved", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.tool_slug}: {self.rating}★"
