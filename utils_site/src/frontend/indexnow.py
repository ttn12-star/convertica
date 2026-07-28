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
import os
import sys

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _indexnow_disabled() -> bool:
    """True when submissions must be skipped (dev, tests, disabled, no key)."""
    is_test_run = "test" in sys.argv or bool(os.environ.get("PYTEST_CURRENT_TEST"))

    if (
        not getattr(settings, "INDEXNOW_ENABLED", False)
        or getattr(settings, "DEBUG", False)
        or is_test_run
    ):
        if is_test_run:
            logger.debug("IndexNow submission skipped in test run")
        elif getattr(settings, "DEBUG", False):
            logger.debug("IndexNow submission skipped in DEBUG mode")
        else:
            logger.debug("IndexNow is disabled in settings")
        return True

    if not getattr(settings, "INDEXNOW_KEY", None):
        logger.warning("INDEXNOW_KEY not set in settings")
        return True

    return False


def submit_url_to_indexnow(url: str) -> bool:
    """
    Submit a single URL to IndexNow via the single-URL GET endpoint.

    Bing Webmaster Tools flags the urlList POST form ("IndexNow is in batch
    mode") because routine batches read as "everything changed" and delay
    indexing. Per-URL GET on real change is the mode they ask for; the batch
    form below is kept for one-shot backfills only.

    Args:
        url: Full URL to submit (e.g., https://convertica.net/en/pdf-to-word/)

    Returns:
        True if submission was successful, False otherwise
    """
    if _indexnow_disabled():
        return False

    try:
        response = requests.get(
            "https://api.indexnow.org/indexnow",
            params={"url": url, "key": settings.INDEXNOW_KEY},
            timeout=10,
        )
    except requests.exceptions.Timeout:
        logger.warning("IndexNow API request timed out")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"IndexNow API request failed: {e}")
        return False

    if response.status_code in (200, 202):
        logger.info(f"Submitted {url} to IndexNow ({response.status_code})")
        return True

    logger.warning(f"IndexNow returned status {response.status_code} for {url}")
    return False


def submit_urls_to_indexnow(urls: list[str]) -> bool:
    """
    Submit multiple URLs to IndexNow API in one batch request.

    Batch mode — use only for one-shot backfills (see the
    submit_sitemap_indexnow management command). Routine per-change pings must
    go through submit_url_to_indexnow instead.

    Args:
        urls: List of full URLs to submit

    Returns:
        True if submission was successful, False otherwise
    """
    if _indexnow_disabled():
        return False

    indexnow_key = settings.INDEXNOW_KEY

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
