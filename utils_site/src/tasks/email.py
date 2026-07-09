"""
Email tasks for Convertica.

These tasks handle asynchronous email sending to avoid blocking
the main request thread, especially when SMTP is slow or unavailable.
"""

import smtplib
import socket

from celery import shared_task
from django.core.mail import EmailMultiAlternatives, send_mail
from src.api.logging_utils import get_logger

# django-anymail isn't a hard dependency in dev; mirror the lazy import the
# account adapter uses so the retry tuple still matches ESP HTTP-API errors.
try:
    from anymail.exceptions import AnymailError
except ImportError:  # pragma: no cover - anymail is in requirements.txt

    class AnymailError(Exception):  # type: ignore[no-redef]
        """Sentinel placeholder when django-anymail is not installed."""


logger = get_logger(__name__)

# Timeout for SMTP connection (in seconds)
EMAIL_TIMEOUT = 30

# Infra failures worth retrying in the background: network/SMTP problems and
# ESP HTTP-API errors. Anything else (bad message, code bug) fails fast.
_RETRYABLE_EMAIL_EXCEPTIONS: tuple[type[BaseException], ...] = (
    OSError,
    smtplib.SMTPException,
    AnymailError,
)


@shared_task(
    name="email.send_account_email",
    queue="default",
    bind=True,
    max_retries=5,
    soft_time_limit=60,
    time_limit=90,
)
def send_account_email(
    self,
    subject: str,
    body: str,
    from_email: str,
    to: list[str],
    html_body: str | None = None,
):
    """Deliver a pre-rendered allauth account email.

    ``CustomAccountAdapter.send_mail`` renders the message in-request (so
    template bugs still surface there) and queues this task, keeping ESP
    latency and outages off the gunicorn workers. Transient failures are
    retried with exponential backoff; after the final retry the exception
    propagates and Sentry picks it up.
    """
    msg = EmailMultiAlternatives(
        subject=subject, body=body, from_email=from_email, to=to
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")

    try:
        msg.send()
    except _RETRYABLE_EMAIL_EXCEPTIONS as exc:
        if self.request.is_eager:
            # Inline mode (dev/console, integration tests): propagate so the
            # adapter translates it into the controlled 503 path.
            raise
        logger.warning(
            "Account email send failed (attempt %d/%d): %s",
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
            extra={"event": "account_email_retry", "recipients": to},
        )
        raise self.retry(
            exc=exc, countdown=min(600, 60 * 2**self.request.retries)
        ) from exc

    logger.info(
        "Account email sent",
        extra={"event": "account_email_sent", "recipients": to},
    )


@shared_task(
    name="email.send_premium_email",
    queue="default",
    bind=True,
    max_retries=3,
    soft_time_limit=60,
    time_limit=90,
)
def send_premium_email(self, user_id: int, kind: str, lang: str = ""):
    """Render and send a localized premium email (welcome / renewal).

    Runs off the webhook request: the handler only enqueues (user_id, kind,
    lang), so ESP latency never ties up the webhook response. The email body
    lives in per-language templates ``emails/premium/{kind}_{lang}.txt`` whose
    first line is the subject. Rendering happens here (deterministic; a template
    bug fails fast to Sentry), then delivery reuses the vetted
    ``send_account_email`` task so retries/backoff are handled in one place.
    """
    from django.conf import settings
    from django.template.loader import render_to_string
    from django.urls import NoReverseMatch, reverse
    from django.utils import translation
    from src.users.models import User

    if kind not in ("welcome", "renewal"):
        logger.error("send_premium_email: unknown kind %r", kind)
        return

    user = User.objects.filter(id=user_id).first()
    if not user:
        logger.warning("send_premium_email: user %s no longer exists", user_id)
        return

    supported = {code for code, _label in settings.LANGUAGES}
    lang = lang if lang in supported else settings.LANGUAGE_CODE
    greeting_name = (getattr(user, "first_name", "") or user.username or "").strip()
    site_url = settings.SITE_URL.rstrip("/")

    with translation.override(lang):
        try:
            profile_url = site_url + reverse("users:profile")
        except NoReverseMatch:  # pragma: no cover - profile route always exists
            profile_url = site_url + "/users/profile/"
        context = {
            "greeting_name": greeting_name,
            "site_url": site_url,
            "profile_url": profile_url,
            "support_email": getattr(
                settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL
            ),
            "email_lang": lang,
            "rtl": lang == "ar",
        }
        text = render_to_string(f"emails/premium/{kind}_{lang}.txt", context)
        html_body = render_to_string(f"emails/premium/{kind}_{lang}.html", context)

    subject, _sep, body = text.partition("\n")
    send_account_email.delay(
        subject=subject.strip(),
        body=body.strip("\n"),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        html_body=html_body,
    )
    logger.info(
        "Premium %s email queued",
        kind,
        extra={"event": "premium_email_queued", "user_id": user_id, "lang": lang},
    )


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
