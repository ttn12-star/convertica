"""Pre-fetch every URL in the sitemap to populate Django's view cache.

The slow-page warnings Ahrefs flagged (~5s TTFB) are cold-cache misses on
rarely-visited language variants. The view-level @cache_page decorators on
tool/blog pages cache for 30-60 min, so a single GET per URL keeps every
page warm for the next visitor (and for any external crawler).

Run on a 30-minute cron (TTL is 60 min, so 30 min keeps cache fresh):
    python manage.py warm_cache

Options:
    --concurrency N  - parallel requests (default 4)
    --base-url URL   - override base URL (default: SITE_URL setting)
"""

import concurrent.futures
import re
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


def fetch_sitemap_urls(base_url: str) -> list[str]:
    """Pull URLs from the sitemap index and per-language sitemaps."""
    index_url = f"{base_url}/sitemap.xml"
    try:
        resp = requests.get(index_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot fetch sitemap index {index_url}: {exc}") from exc

    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    page_urls: list[str] = []
    for sm_url in sitemap_urls:
        try:
            r = requests.get(sm_url, timeout=30)
            r.raise_for_status()
            page_urls.extend(re.findall(r"<loc>([^<]+)</loc>", r.text))
        except requests.RequestException as exc:
            print(f"  skip {sm_url}: {exc}")
    # Dedupe while preserving order
    seen = set()
    out: list[str] = []
    for u in page_urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


class Command(BaseCommand):
    help = "Warm view cache by fetching every URL in the sitemap."

    def add_arguments(self, parser):
        parser.add_argument("--concurrency", type=int, default=4)
        parser.add_argument("--base-url", default=None)
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Per-request timeout in seconds (default 30)",
        )

    def handle(self, *args, **opts):
        base_url = opts["base_url"] or getattr(
            settings, "SITE_URL", "https://convertica.net"
        )
        base_url = base_url.rstrip("/")
        timeout = opts["timeout"]

        self.stdout.write(f"Reading sitemap from {base_url}/sitemap.xml ...")
        urls = fetch_sitemap_urls(base_url)
        self.stdout.write(f"Found {len(urls)} URL(s).")

        slow: list[tuple[str, float, int]] = []
        ok = err = 0

        def _hit(url: str) -> tuple[str, float, int | None, str | None]:
            t0 = time.monotonic()
            try:
                # X-Cache-Warm header marks this as a non-user request so
                # views/middleware can decide to skip side effects (analytics).
                r = requests.get(
                    url,
                    timeout=timeout,
                    headers={
                        "X-Cache-Warm": "1",
                        "User-Agent": "convertica-cache-warmer/1.0",
                    },
                )
                return url, time.monotonic() - t0, r.status_code, None
            except requests.RequestException as exc:
                return url, time.monotonic() - t0, None, str(exc)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=opts["concurrency"]
        ) as pool:
            for url, dt, code, err_msg in pool.map(_hit, urls):
                if err_msg or code is None or code >= 500:
                    err += 1
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {url} ({code}) {err_msg or ''}")
                    )
                else:
                    ok += 1
                    if dt > 2.0:
                        slow.append((url, dt, code))

        self.stdout.write(
            self.style.SUCCESS(f"\nWarmed {ok}/{len(urls)} OK, {err} error(s).")
        )
        if slow:
            self.stdout.write(
                "\nSlow first-hit responses (>2s — likely deserving deeper caching):"
            )
            for url, dt, code in sorted(slow, key=lambda x: -x[1])[:10]:
                self.stdout.write(f"  {dt:5.2f}s  [{code}]  {url}")
