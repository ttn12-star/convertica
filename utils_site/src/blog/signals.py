"""Signals for blog models to automatically notify search engines via IndexNow."""

import logging
import os
import sys

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="blog.Article")
def notify_indexnow_on_article_save(
    sender, instance, created, **kwargs
):  # noqa: ARG001
    """
    Automatically submit article URL to IndexNow when article is published or updated.

    Args:
        sender: The model class (Article)
        instance: The actual instance being saved
        created: Boolean, True if this is a new record, False otherwise
        **kwargs: Additional keyword arguments
    """
    # Only submit to IndexNow if IndexNow is enabled
    if not getattr(settings, "INDEXNOW_ENABLED", False):
        return

    # Only submit published articles
    if instance.status != "published":
        return

    # Skip if in DEBUG/test mode
    is_test_run = "test" in sys.argv or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if getattr(settings, "DEBUG", False):
        logger.debug("IndexNow submission skipped in DEBUG mode")
        return
    if is_test_run:
        logger.debug("IndexNow submission skipped in test run")
        return

    try:
        from src.frontend.indexnow import submit_url_to_indexnow

        # Get site base URL
        site_url = getattr(settings, "SITE_BASE_URL", "https://convertica.net")

        # One ping per locale the article actually exists in. The English base
        # always counts; others only when present in the translations JSON —
        # the same set the sitemap emits. Ping the locales, not just /en/:
        # otherwise the translated URLs are never announced and the only thing
        # that ever covered them was the daily full-sitemap batch sweep (which
        # Bing flags as batch-mode abuse).
        default_language = getattr(settings, "LANGUAGE_CODE", "en")
        locales = [default_language] + [
            lang for lang in (instance.translations or {}) if lang != default_language
        ]

        submitted = 0
        for lang in locales:
            if submit_url_to_indexnow(f"{site_url}/{lang}/blog/{instance.slug}/"):
                submitted += 1

        if submitted:
            logger.info(
                "Article '%s' (slug: %s) submitted to IndexNow for %d/%d locale(s)",
                instance.title_en,
                instance.slug,
                submitted,
                len(locales),
            )
        else:
            logger.warning(
                "Failed to submit article '%s' (slug: %s) to IndexNow",
                instance.title_en,
                instance.slug,
            )

    except ImportError:
        logger.error(
            "Failed to import submit_url_to_indexnow - IndexNow integration not available"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            "Error submitting article to IndexNow: %s",
            str(e),
            exc_info=True,
        )
