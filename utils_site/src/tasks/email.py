"""
Email tasks for Convertica.

These tasks handle asynchronous email sending to avoid blocking
the main request thread, especially when SMTP is slow or unavailable.
"""

import socket

from celery import shared_task
from django.core.mail import send_mail
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

# Timeout for SMTP connection (in seconds)
EMAIL_TIMEOUT = 30


@shared_task(
    name="email.send_contact_form",
    queue="default",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute between retries
    soft_time_limit=60,
    time_limit=90,
)
def send_contact_form_email(
    self,
    subject: str,
    message: str,
    from_email: str,
    recipient_email: str,
    user_email: str,
    user_ip: str,
):
    """
    Send contact form email asynchronously.

    Args:
        subject: Email subject
        message: Email body
        from_email: Sender email (system email)
        recipient_email: Recipient email (contact email)
        user_email: Email of the user who submitted the form
        user_ip: IP address of the user
    """
    try:
        # Set socket timeout to avoid hanging
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(EMAIL_TIMEOUT)

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

            logger.info(
                "Contact form email sent successfully",
                extra={
                    "user_email": user_email,
                    "user_ip": user_ip,
                    "recipient": recipient_email,
                },
            )

            return {
                "status": "success",
                "recipient": recipient_email,
                "user_email": user_email,
            }

        finally:
            # Restore original timeout
            socket.setdefaulttimeout(old_timeout)

    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning(
            "Failed to send contact form email (attempt %d/%d): %s",
            self.request.retries + 1,
            self.max_retries + 1,
            str(exc),
            extra={
                "user_email": user_email,
                "user_ip": user_ip,
                "error": str(exc),
            },
        )
        # Retry on connection errors
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(
            "Unexpected error sending contact form email: %s",
            str(exc),
            exc_info=True,
            extra={
                "user_email": user_email,
                "user_ip": user_ip,
                "error": str(exc),
            },
        )
        return {
            "status": "error",
            "error": str(exc),
            "user_email": user_email,
        }
