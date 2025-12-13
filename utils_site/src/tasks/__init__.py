"""
Celery tasks for Convertica.

This package contains all asynchronous tasks for PDF processing,
file conversions, email sending, and other background operations.
"""

# Import tasks to register them with Celery
from .email import send_contact_form_email
from .maintenance import cleanup_temp_files, update_statistics
from .telegram_service import send_telegram_message

__all__ = [
    "send_contact_form_email",
    "cleanup_temp_files",
    "update_statistics",
    "send_telegram_message",
]
