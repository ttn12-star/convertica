#!/usr/bin/env python3
"""Styled screenshots of the two premium dashboards for their public landings.

Companion to gen_tool_screenshots.py (imports its compose/save_variants):
the dashboards are premium-gated, so this script logs in as a premium user
and seeds localStorage with believable demo data before shooting.

Usage (one-off container from the worktree, premium user seeded):
    SHOT_BASE=http://127.0.0.1:8056/en/ \
    SHOT_EMAIL=premium-e2e@test.local SHOT_PASSWORD=... \
    python scripts/gen_premium_dashboard_screenshots.py

Output: static/images/tools/{background-tasks,saved-workflows}.{jpg,webp}
(+ -card.webp), i.e. the slugs of the PUBLIC landing pages, so
_tool_screenshot_paths() and the image sitemap pick them up automatically.
"""

import json
import os
import sys

from gen_tool_screenshots import BASE, CLIP, compose, save_variants
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("SHOT_EMAIL", "premium-e2e@test.local")
PASSWORD = os.environ.get("SHOT_PASSWORD", "e2e-pass-123")

BG_TASKS = [
    {
        "taskId": "0e67a1b2-demo-0001",
        "conversionType": "pdf_to_word",
        "originalFilename": "plan_to_defeat_titans_v2_FINAL.pdf",
        "outputFilename": "plan_to_defeat_titans_v2_FINAL_convertica.docx",
        "status": "success",
        "taskToken": "",
    },
    {
        "taskId": "0e67a1b2-demo-0002",
        "conversionType": "epub_to_pdf",
        "originalFilename": "fellowship_travel_notes.epub",
        "outputFilename": "",
        "status": "processing",
        "taskToken": "",
    },
    {
        "taskId": "0e67a1b2-demo-0003",
        "conversionType": "compress_pdf",
        "originalFilename": "voyager_golden_record_tracklist.pdf",
        "outputFilename": "voyager_golden_record_tracklist_compressed.pdf",
        "status": "success",
        "taskToken": "",
    },
]

WORKFLOWS = [
    {
        "id": "demo-1",
        "name": "Weekly Invoices to PDF",
        "notes": "Batch of 10, one ZIP for accounting.",
        "toolUrl": "/en/batch-converter/",
    },
    {
        "id": "demo-2",
        "name": "eBook to Print PDF",
        "notes": "Check margins before sending to print.",
        "toolUrl": "/en/epub-to-pdf/",
    },
    {
        "id": "demo-3",
        "name": "Scans to Editable Word",
        "notes": "Enable OCR, language: auto.",
        "toolUrl": "/en/scanned-pdf-to-word/",
    },
]


def shoot(page, url_path: str, seed_js: str) -> bytes:
    page.goto(BASE + url_path, wait_until="networkidle", timeout=60000)
    page.evaluate(seed_js)
    page.reload(wait_until="networkidle")
    # dashboards are max-w-6xl (wider than tool pages) — zoom out a bit more
    # than the pipeline's .85 and center the clip on the card horizontally
    page.add_style_tag(content="#cookie-banner{display:none !important} body{zoom:.72}")
    page.wait_for_timeout(800)
    page.evaluate("window.scrollTo(0,0)")
    clip = dict(CLIP)
    sec = page.locator("main section").first.bounding_box()
    if sec:
        clip["x"] = max(0, sec["x"] + sec["width"] / 2 - CLIP["width"] / 2)
    h1 = page.locator("h1").first.bounding_box()
    if h1:
        page_h = page.evaluate("document.documentElement.scrollHeight")
        clip["y"] = max(0, min(h1["y"] - 60, page_h - CLIP["height"] - 8))
    return page.screenshot(type="png", clip=clip, full_page=True)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1280, "height": 900}, device_scale_factor=2
        )
        # keep the fake "processing" demo task spinning instead of erroring
        page.route(
            "**/api/tasks/**",
            lambda route: route.fulfill(
                content_type="application/json",
                body='{"status": "PROGRESS", "progress": 45}',
            ),
        )
        compose_page = browser.new_page(
            viewport={"width": 1200, "height": 750}, device_scale_factor=2
        )

        page.goto(BASE + "users/login/", wait_until="networkidle")
        page.fill("input[name=email]", EMAIL)
        page.fill("input[name=password]", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url("**/profile/**", timeout=15000)

        now_offsets = [8, 2, 15]  # minutes ago per BG task
        bg_seed = (
            "() => localStorage.setItem('convertica_bg_tasks', JSON.stringify("
            + json.dumps(BG_TASKS)
            + ".map((t, i) => ({...t, startedAt: Date.now() - "
            + json.dumps(now_offsets)
            + "[i] * 60000}))))"
        )
        raw = shoot(page, "premium/background-center/", bg_seed)
        final = compose(compose_page, raw, "premium/background-center/", 7)
        save_variants(final, "background-tasks")
        print("  + background-tasks")

        wf_seed = (
            "() => localStorage.setItem('convertica_premium_workflows_v1',"
            " JSON.stringify("
            + json.dumps(WORKFLOWS)
            + ".map((w, i) => ({...w, createdAt: Date.now() - i * 86400000}))))"
        )
        raw = shoot(page, "premium/workflows/", wf_seed)
        final = compose(compose_page, raw, "premium/workflows/", 18)
        save_variants(final, "saved-workflows")
        print("  + saved-workflows")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
