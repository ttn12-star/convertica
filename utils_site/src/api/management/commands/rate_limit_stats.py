"""
Management command to view rate limit statistics.

Usage:
    python manage.py rate_limit_stats
    python manage.py rate_limit_stats --group api_conversion
    python manage.py rate_limit_stats --hours 24
"""

from django.core.management.base import BaseCommand
from src.api.rate_limit_utils import get_rate_limit_stats


class Command(BaseCommand):
    help = "Display rate limit statistics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            type=str,
            help="Specific rate limit group to show stats for",
            default=None,
        )
        parser.add_argument(
            "--hours", type=int, help="Number of hours to look back", default=1
        )

    def handle(self, *args, **options):
        group = options["group"]
        hours = options["hours"]

        self.stdout.write(
            self.style.SUCCESS(f"\n📊 Rate Limit Statistics (last {hours} hour(s))\n")
        )

        stats = get_rate_limit_stats(group=group, hours=hours)

        for grp, data in stats.items():
            self.stdout.write(self.style.WARNING(f"\n{grp.upper()}:"))
            self.stdout.write(f'  Total requests: {data["total"]}')
            self.stdout.write(
                f'  Premium users: {data["premium"]} ({self._percentage(data["premium"], data["total"])}%)'
            )
            self.stdout.write(
                f'  Authenticated: {data["authenticated"]} ({self._percentage(data["authenticated"], data["total"])}%)'
            )
            self.stdout.write(
                f'  Anonymous: {data["anonymous"]} ({self._percentage(data["anonymous"], data["total"])}%)'
            )
            self.stdout.write(self.style.ERROR(f'  Blocked (IP): {data["blocked_ip"]}'))
            self.stdout.write(
                self.style.ERROR(f'  Blocked (User): {data["blocked_user"]}')
            )

        self.stdout.write(self.style.SUCCESS("\n✅ Done!\n"))

    def _percentage(self, part, total):
        """Calculate percentage."""
        if total == 0:
            return 0
        return round((part / total) * 100, 1)
