"""Post-deploy cache clear that preserves cookieless unique-visitor counts.

`cache.clear()` FLUSHDBs the default Redis cache DB — which also destroys the
per-day `uv:<date>` HyperLogLog keys holding the unique-visitor counts (see
frontend.middleware.TrafficCountingMiddleware). Those live only in Redis, so a
plain clear on every deploy resets the day's uniques to zero (page views, kept
in Postgres, are unaffected). This command flushes everything on the cache DB
*except* the `uv:*` keys, so deploys no longer truncate unique visitors.
"""

from django.core.management.base import BaseCommand

# uv:* keys are written via a raw Redis connection with no django-redis key
# prefix, so this bytes-prefix test cleanly separates them from cache entries.
_UNIQUE_KEY_PREFIX = b"uv:"


class Command(BaseCommand):
    help = "Clear the Django cache but preserve unique-visitor HLLs (uv:*)."

    def handle(self, *args, **options):
        try:
            from django_redis import get_redis_connection

            conn = get_redis_connection("default")
        except Exception as exc:  # Redis down / not django-redis — nothing to do.
            self.stderr.write(f"Redis unavailable, cache not cleared: {exc}")
            return

        deleted = 0
        batch = []
        for key in conn.scan_iter(match="*", count=500):
            if key.startswith(_UNIQUE_KEY_PREFIX):
                continue
            batch.append(key)
            if len(batch) >= 500:
                deleted += conn.delete(*batch)
                batch = []
        if batch:
            deleted += conn.delete(*batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared {deleted} cache key(s), preserved uv:* uniques."
            )
        )
