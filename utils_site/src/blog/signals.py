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

        # Get absolute URL for the article
        # Article.get_absolute_url() returns relative URL like "/en/blog/article-slug/"
        article_relative_url = instance.get_absolute_url()

        # Construct full URL
        full_url = f"{site_url}{article_relative_url}"

        # Submit to IndexNow (async in background, won't block request)
        # Note: submit_url_to_indexnow makes HTTP request, but it's fast and non-blocking
        success = submit_url_to_indexnow(full_url)

        if success:
            logger.info(
                "Article '%s' (slug: %s) submitted to IndexNow successfully",
                instance.title_en,
                instance.slug,
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
