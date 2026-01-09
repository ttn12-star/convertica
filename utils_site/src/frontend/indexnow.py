"""IndexNow integration for instant search engine indexing.

IndexNow is a protocol that allows websites to instantly notify search engines
about new, updated, or deleted content. This helps with faster indexing.

Supported search engines:
- Microsoft Bing
- Yandex
- Seznam
- (Google is testing)
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def submit_url_to_indexnow(url: str) -> bool:
    """
    Submit a single URL to IndexNow API.

    Args:
        url: Full URL to submit (e.g., https://convertica.net/en/pdf-to-word/)

    Returns:
        True if submission was successful, False otherwise
    """
    return submit_urls_to_indexnow([url])


def submit_urls_to_indexnow(urls: list[str]) -> bool:
    """
    Submit multiple URLs to IndexNow API.

    Args:
        urls: List of full URLs to submit

    Returns:
        True if submission was successful, False otherwise
    """
    # Check if IndexNow is enabled
    if not getattr(settings, "INDEXNOW_ENABLED", False):
        logger.debug("IndexNow is disabled in settings")
        return False

    # Get IndexNow key from settings
    indexnow_key = getattr(settings, "INDEXNOW_KEY", None)
    if not indexnow_key:
        logger.warning("INDEXNOW_KEY not set in settings")
        return False

    # Get site URL
    site_url = getattr(settings, "SITE_BASE_URL", "https://convertica.net")
    host = site_url.replace("https://", "").replace("http://", "").rstrip("/")

    # Prepare payload according to IndexNow specification
    # Note: keyLocation is used only for validation - the key file must be accessible
    # at {site_url}/{indexnow_key}.txt, but keyLocation should NOT be in the payload
    payload = {
        "host": host,
        "key": indexnow_key,
        "urlList": urls,
    }

    try:
        # Submit to IndexNow API
        response = requests.post(
            "https://api.indexnow.org/indexnow",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10,
        )

        if response.status_code == 200:
            logger.info(f"Successfully submitted {len(urls)} URLs to IndexNow")
            return True
        elif response.status_code == 202:
            logger.info(
                f"IndexNow accepted {len(urls)} URLs (202 - already submitted recently)"
            )
            return True
        else:
            logger.warning(
                f"IndexNow returned status {response.status_code}: {response.text}"
            )
            return False

    except requests.exceptions.Timeout:
        logger.warning("IndexNow API request timed out")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"IndexNow API request failed: {e}")
        return False


def get_indexnow_key_content() -> str:
    """
    Get the content for the IndexNow key file.

    Returns:
        The IndexNow key string
    """
    return getattr(settings, "INDEXNOW_KEY", "")
