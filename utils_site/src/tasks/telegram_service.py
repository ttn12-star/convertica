import requests
from celery import shared_task
from django.conf import settings
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

TELEGRAM_TIMEOUT = 10


@shared_task(
    name="telegram_service.send_message",
    queue="default",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60,
)
def send_telegram_message(
    self,
    text: str,
    chat_id: str | None = None,
    bot_token: str | None = None,
):
    """
    Send a Telegram message asynchronously.

    Args:
        text: Message text (max 4096 characters)
        chat_id: Optional override for chat ID
        bot_token: Optional override for bot token
    """
    bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not bot_token or not chat_id:
        logger.warning(
            "Telegram bot token or chat ID not configured",
            extra={
                "chat_id": chat_id,
                "has_bot_token": bool(bot_token),
            },
        )
        return {
            "status": "error",
            "error": "Telegram credentials not configured",
        }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=TELEGRAM_TIMEOUT,
        )
        response.raise_for_status()

        logger.info(
            "Telegram message sent successfully",
            extra={
                "chat_id": chat_id,
                "message_length": len(text),
            },
        )

        return {
            "status": "success",
            "chat_id": chat_id,
        }

    except requests.exceptions.RequestException as exc:
        logger.warning(
            "Failed to send Telegram message (attempt %d/%d): %s",
            self.request.retries + 1,
            self.max_retries + 1,
            str(exc),
            extra={
                "chat_id": chat_id,
                "error": str(exc),
            },
        )
        # Retry on network / API errors
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error(
            "Unexpected error sending Telegram message: %s",
            str(exc),
            exc_info=True,
            extra={
                "chat_id": chat_id,
                "error": str(exc),
            },
        )
        return {
            "status": "error",
            "error": str(exc),
        }
