"""Tool feedback app configuration."""

from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.feedback"
    verbose_name = "Tool Feedback"
