"""Show consent-free traffic: page views (DB) + approx unique visitors (Redis).

Real, bot-filtered human traffic recorded by ``TrafficCountingMiddleware`` —
independent of the cookie banner. Use this to sanity-check GA4 (which only sees
users who accept cookies) and to see which pages actually get read by people
rather than crawlers.

Examples::

    manage.py traffic_stats                 # last 30 days, daily totals + top pages
    manage.py traffic_stats --days 7
    manage.py traffic_stats --contains /blog/   # rank blog articles by views
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone
from src.frontend.middleware import _redis


class Command(BaseCommand):
    help = "Consent-free traffic: page views (DB) + approx unique visitors (Redis HLL)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Window size in days.")
        parser.add_argument(
            "--contains",
            default="",
            help="Only count paths containing this substring (e.g. /blog/).",
        )
        parser.add_argument(
            "--top", type=int, default=20, help="How many top pages to list."
        )

    def handle(self, *args, **opts):
        from src.users.models import PageViewDaily

        days = max(1, opts["days"])
        needle = opts["contains"]
        today = timezone.now().date()
        start = today - timedelta(days=days - 1)

        rows = PageViewDaily.objects.filter(date__gte=start)
        if needle:
            rows = rows.filter(path__contains=needle)

        views_by_day = dict(rows.values_list("date").annotate(total=Sum("views")))
        conn = _redis()

        title = f"Traffic — last {days} day(s)"
        if needle:
            title += f", paths containing '{needle}'"
        self.stdout.write(self.style.MIGRATE_HEADING(title))
        self.stdout.write(f"{'date':<12}{'views':>10}{'uniques':>10}")
        total_views = 0
        for i in range(days):
            d = start + timedelta(days=i)
            v = views_by_day.get(d, 0)
            total_views += v
            # Uniques are site-wide (not path-filterable): the HLL is keyed by
            # day only. Shown as-is; suppressed when a --contains filter is set
            # to avoid implying the count is scoped to those paths.
            if needle:
                u = "—"
            else:
                u = conn.pfcount(f"uv:{d.isoformat()}") if conn is not None else "n/a"
            self.stdout.write(f"{d.isoformat():<12}{v:>10}{str(u):>10}")
        self.stdout.write(f"{'TOTAL':<12}{total_views:>10}")

        top = (
            rows.values("path")
            .annotate(total=Sum("views"))
            .order_by("-total")[: opts["top"]]
        )
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Top {opts['top']} pages"))
        for entry in top:
            self.stdout.write(f"{entry['total']:>10}  {entry['path']}")
