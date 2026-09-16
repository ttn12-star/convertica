"""Bulk-submit every sitemap URL to IndexNow.

Ahrefs flagged ~463 "Pages to submit to IndexNow" notices — those are
indexable URLs that haven't been pinged yet. Article publishes hit the
signal handler going forward, but historical pages need a one-shot push.

Run on prod (after setting INDEXNOW_ENABLED=True and INDEXNOW_KEY=<32-char-hex>):
    python manage.py submit_sitemap_indexnow

IndexNow's API accepts up to 10,000 URLs per request, but Bing recommends
batches of ≤200 to avoid rate limits.
"""

import re
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from src.frontend.indexnow import submit_urls_to_indexnow

BATCH_SIZE = 200


def fetch_sitemap_urls(base_url: str) -> list[str]:
    index_url = f"{base_url}/sitemap.xml"
    resp = requests.get(index_url, timeout=30)
    resp.raise_for_status()
    sitemap_urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    page_urls: list[str] = []
    for sm in sitemap_urls:
        try:
            r = requests.get(sm, timeout=30)
            r.raise_for_status()
            page_urls.extend(re.findall(r"<loc>([^<]+)</loc>", r.text))
        except requests.RequestException as exc:
            print(f"  skip {sm}: {exc}")
    seen = set()
    out = []
    for u in page_urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


class Command(BaseCommand):
    help = "Submit every URL in sitemap.xml to IndexNow."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default=None)
        parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)

    def handle(self, *args, **opts):
        if not getattr(settings, "INDEXNOW_ENABLED", False):
            raise CommandError(
                "INDEXNOW_ENABLED is False. Set INDEXNOW_ENABLED=True and "
                "INDEXNOW_KEY=<32-char-hex> in .env on prod, then re-run."
            )
        if not getattr(settings, "INDEXNOW_KEY", ""):
            raise CommandError("INDEXNOW_KEY not set.")

        base_url = (
            opts["base_url"]
            or getattr(settings, "SITE_BASE_URL", "https://convertica.net")
        ).rstrip("/")

        self.stdout.write(f"Fetching sitemap from {base_url} ...")
        urls = fetch_sitemap_urls(base_url)
        self.stdout.write(
            f"Submitting {len(urls)} URL(s) in batches of {opts['batch_size']}..."
        )

        ok_batches = 0
        fail_batches = 0
        batch = opts["batch_size"]
        for i in range(0, len(urls), batch):
            chunk = urls[i : i + batch]
            success = submit_urls_to_indexnow(chunk)
            if success:
                ok_batches += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ batch {i//batch + 1}: {len(chunk)} URLs")
                )
            else:
                fail_batches += 1
                self.stdout.write(self.style.ERROR(f"  ✗ batch {i//batch + 1}: failed"))
            # Be polite — Bing rate-limit recommendation
            time.sleep(2)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {ok_batches} batch(es) OK, {fail_batches} failed."
            )
        )
