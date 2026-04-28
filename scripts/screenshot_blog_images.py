"""Generate blog illustration screenshots via Playwright.

Run inside the web container:
    docker compose exec -T web python /app/scripts/screenshot_blog_images.py

Saves JPGs into /app/static/blog/images/ which is then collected by collectstatic.
Resolution / viewport is tuned so the images render well in 700-800 px content
columns without ballooning page weight.
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/app/static/blog/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE = "http://localhost:8003"

# (filename, url, viewport_w, viewport_h, full_page)
SHOTS: list[tuple[str, str, int, int, bool]] = [
    ("tool-compress.jpg", f"{BASE}/en/pdf-organize/compress/", 1280, 800, False),
    ("tool-merge.jpg", f"{BASE}/en/pdf-organize/merge/", 1280, 800, False),
    ("tool-split.jpg", f"{BASE}/en/pdf-organize/split/", 1280, 800, False),
    ("tool-organize.jpg", f"{BASE}/en/pdf-organize/", 1280, 800, False),
    ("tool-watermark.jpg", f"{BASE}/en/pdf-edit/add-watermark/", 1280, 800, False),
    ("tool-rotate.jpg", f"{BASE}/en/pdf-edit/rotate/", 1280, 800, False),
    ("tool-protect.jpg", f"{BASE}/en/pdf-security/protect/", 1280, 800, False),
    ("tool-pdf-to-word.jpg", f"{BASE}/en/pdf-to-word/", 1280, 800, False),
    ("tool-word-to-pdf.jpg", f"{BASE}/en/word-to-pdf/", 1280, 800, False),
    ("tool-pdf-to-excel.jpg", f"{BASE}/en/pdf-to-excel/", 1280, 800, False),
    ("tool-jpg-to-pdf.jpg", f"{BASE}/en/jpg-to-pdf/", 1280, 800, False),
    ("tool-all.jpg", f"{BASE}/en/all-tools/", 1280, 800, False),
    ("home-hero.jpg", f"{BASE}/en/", 1280, 800, False),
]


def main() -> None:
    failures: list[tuple[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for filename, url, vw, vh, full in SHOTS:
            ctx = browser.new_context(viewport={"width": vw, "height": vh})
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(800)  # let fonts/css settle
                target = OUT_DIR / filename
                page.screenshot(
                    path=str(target),
                    type="jpeg",
                    quality=80,
                    full_page=full,
                )
                print(f"OK  {filename}  {os.path.getsize(target)//1024} KB")
            except Exception as e:
                failures.append((filename, str(e)))
                print(f"ERR {filename}: {e}")
            finally:
                ctx.close()
        browser.close()
    if failures:
        print(f"\n{len(failures)} failures:")
        for f, msg in failures:
            print(f"  - {f}: {msg}")


if __name__ == "__main__":
    main()
