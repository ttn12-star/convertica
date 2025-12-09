"""
Management command to clear Django cache.

Usage:
    python manage.py clear_cache
    python manage.py clear_cache --key homepage_latest_articles
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear Django cache (Redis)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            type=str,
            help="Clear specific cache key only (e.g., homepage_latest_articles)",
        )

    def handle(self, *args, **options):
        key = options.get("key")

        if key:
            cache.delete(key)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Cache key '{key}' cleared successfully!")
            )
        else:
            cache.clear()
            self.stdout.write(self.style.SUCCESS("✅ All cache cleared successfully!"))
