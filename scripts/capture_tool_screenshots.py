#!/usr/bin/env python3
"""Capture real tool screenshots from convertica.net for use as blog inline images.

For each tool page we grab two distinct, on-brand shots:
  * ``tool-<key>-hero.jpg``     - title + upload dropzone (labels the tool)
  * ``tool-<key>-options.jpg``  - the tool-specific settings/steps panel below

Output: static/blog/images/. Crops the centered content column and avoids the
sticky header. Re-run to refresh; idempotent.

    python scripts/capture_tool_screenshots.py            # all
    python scripts/capture_tool_screenshots.py rotate ... # only some keys
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "blog" / "images"
BASE = "https://convertica.net/en/"

# key -> tool page path (under /en/)
TOOLS = {
    "compress": "pdf-organize/compress/",
    "excel-to-pdf": "excel-to-pdf/",
    "pdf-to-word": "pdf-to-word/",
    "image-to-text": "image/to-text/",
    "zip-protect": "archive/protect/",
    "merge": "pdf-organize/merge/",
    "pdf-protect": "pdf-security/protect/",
    "all-tools": "all-tools/",
    "remove-pages": "pdf-organize/remove-pages/",
    "organize": "pdf-organize/organize/",
    "rotate": "pdf-edit/rotate/",
    "split": "pdf-organize/split/",
    "watermark": "pdf-edit/add-watermark/",
    "page-numbers": "pdf-edit/add-page-numbers/",
    "pdf-to-jpg": "pdf-to-jpg/",
    "jpg-to-pdf": "jpg-to-pdf/",
    "sign": "pdf-edit/sign/",
    "crop": "pdf-edit/crop/",
}

# crop boxes in CSS px (content column is centered ~258..1022 at 1280 wide)
HERO_CLIP = {"x": 216, "y": 150, "width": 848, "height": 600}
OPT_CLIP = {"x": 216, "y": 96, "width": 848, "height": 620}


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = argv or list(TOOLS)
    bad = [k for k in keys if k not in TOOLS]
    if bad:
        print(f"Unknown key(s): {bad}", file=sys.stderr)
        return 1
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1280, "height": 860}, device_scale_factor=2
        )
        for key in keys:
            url = BASE + TOOLS[key]
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as exc:
                print(f"  ! {key}: load failed ({exc})", file=sys.stderr)
                continue
            page.wait_for_timeout(1400)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(200)
            hero = OUT / f"tool-{key}-hero.jpg"
            page.screenshot(path=str(hero), type="jpeg", quality=86, clip=HERO_CLIP)
            # second shot: scroll past the dropzone to the tool-specific panel
            page.evaluate("window.scrollBy(0, 600)")
            page.wait_for_timeout(500)
            opt = OUT / f"tool-{key}-options.jpg"
            page.screenshot(path=str(opt), type="jpeg", quality=86, clip=OPT_CLIP)
            print(f"  + {key}: hero + options")
        browser.close()
    print(f"Done: {len(keys)} tool(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
