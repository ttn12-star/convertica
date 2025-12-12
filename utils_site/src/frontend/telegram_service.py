import requests
from django.conf import settings


class TelegramService:
    """Service for sending messages to Telegram."""

    @staticmethod
    def send_message(text: str) -> None:
        """Send a text message to the configured Telegram chat.

        Args:
            text (str): The message text to send. Maximum length is 4096 characters.

        Raises:
            requests.HTTPError: If the request to Telegram API fails.
        """
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text[:4096],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
