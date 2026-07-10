#!/usr/bin/env python3
"""Generate styled marketing screenshots for every public tool page.

Two-phase pipeline:
  1. capture  — Playwright loads the tool page (local one-off container by
     default), stages easter-egg demo files in the picker so the tool looks
     "in action", crops the content column.
  2. compose  — the raw crop is placed inside a browser-chrome card on a
     brand gradient with soft blobs + small original doodles, rendered via
     Playwright (same technique as gen_blog_covers.py) at 1200x750.

Outputs (git-tracked): static/images/tools/<slug>.jpg + .webp + <slug>-card.webp
where slug = url path with '/' -> '-' (e.g. pdf-organize-merge).

    SHOT_BASE=http://127.0.0.1:8056/en/ python scripts/gen_tool_screenshots.py
    python scripts/gen_tool_screenshots.py pdf-to-word image-to-text   # subset
"""
from __future__ import annotations

import base64
import io
import os
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "scripts" / "demo_files"
OUT = ROOT / "static" / "images" / "tools"
BASE = os.environ.get("SHOT_BASE", "http://127.0.0.1:8056/en/")

# All public tool pages (source of truth: frontend/urls.py; premium pages excluded).
TOOL_PATHS = [
    "pdf-to-word/",
    "word-to-pdf/",
    "pdf-to-jpg/",
    "jpg-to-pdf/",
    "pdf-to-excel/",
    "excel-to-pdf/",
    "ppt-to-pdf/",
    "html-to-pdf/",
    "pdf-to-ppt/",
    "pdf-to-html/",
    "pdf-to-markdown/",
    "pdf-to-text/",
    "compare-pdf/",
    "epub-to-pdf/",
    "pdf-to-epub/",
    "scanned-pdf-to-word/",
    # batch-converter/ excluded: redirects anonymous visitors to the login page
    "pdf-edit/rotate/",
    "pdf-edit/add-page-numbers/",
    "pdf-edit/add-watermark/",
    "pdf-edit/crop/",
    "pdf-edit/flatten/",
    "pdf-edit/sign/",
    "image/optimize/",
    "image/convert/",
    "image/heic-to-jpg/",
    "image/to-text/",
    "image/favicon-generator/",
    "image/png-to-ico/",
    "image/jpg-to-ico/",
    "image/svg-to-ico/",
    "image/webp-to-ico/",
    "image/ico-to-png/",
    "pdf-organize/merge/",
    "pdf-organize/split/",
    "pdf-organize/remove-pages/",
    "pdf-organize/extract-pages/",
    "pdf-organize/organize/",
    "pdf-organize/compress/",
    "pdf-security/protect/",
    "pdf-security/unlock/",
    "archive/protect/",
    "archive/unlock/",
]

# demo file per extension; multi-file tools get the list
DEMO_BY_EXT = {
    ".pdf": [
        "plan_to_defeat_titans_v2_FINAL.pdf",
        "chapter_67_storyboard.pdf",
        "hallelujah_chords.pdf",
    ],
    ".docx": ["never_gonna_give_you_up.docx"],
    ".doc": ["never_gonna_give_you_up.docx"],
    ".xlsx": ["totoro_watchlist.xlsx"],
    ".xls": ["totoro_watchlist.xlsx"],
    ".pptx": ["one_more_time_setlist.pptx"],
    ".ppt": ["one_more_time_setlist.pptx"],
    ".jpg": ["much_wow_vacation_photo.jpg"],
    ".jpeg": ["much_wow_vacation_photo.jpg"],
    ".png": ["pixel_heart_collection.png"],
    ".webp": ["level_67_unlocked.webp"],
    ".ico": ["not_a_moon_favicon.ico"],
    ".heic": ["skywalker_family_album.heic"],
    ".svg": ["legendary_sword_logo.svg"],
    ".html": ["hello_there_kenobi.html"],
    ".htm": ["hello_there_kenobi.html"],
    ".txt": ["shrek_screenplay_draft_9.txt"],
    ".md": ["README_secret_lore.md"],
    ".epub": ["fellowship_travel_notes.epub"],
    ".zip": ["winter_is_coming_backup.zip"],
}

# tools that render page previews client-side need extra settle time
PREVIEW_TOOLS = {
    "pdf-edit-crop",
    "pdf-edit-sign",
    "pdf-organize-split",
    "pdf-organize-remove-pages",
    "pdf-organize-extract-pages",
    "pdf-organize-organize",
    "compare-pdf",
}

CLIP = {"x": 216, "y": 96, "width": 848, "height": 560}

# gradient pairs rotated per tool so the set feels varied but on-brand
GRADIENTS = [
    ("#4f46e5", "#7c3aed"),
    ("#4338ca", "#9333ea"),
    ("#2563eb", "#7c3aed"),
    ("#3730a3", "#6d28d9"),
    ("#1d4ed8", "#8b5cf6"),
    ("#4f46e5", "#a855f7"),
]

# small ORIGINAL doodles (no third-party characters) rotated per tool
DOODLES = [
    # paper plane with dotted trail
    """<svg width="72" height="52" viewBox="0 0 72 52" fill="none">
      <path d="M2 40 C 14 34, 26 26, 38 22" stroke="rgba(255,255,255,.55)" stroke-width="2" stroke-dasharray="1 7" stroke-linecap="round"/>
      <path d="M40 8 L68 20 L48 26 L44 38 L40 27 Z" fill="rgba(255,255,255,.85)"/></svg>""",
    # rubber duck
    """<svg width="56" height="48" viewBox="0 0 56 48" fill="none">
      <ellipse cx="26" cy="32" rx="20" ry="12" fill="rgba(255,214,10,.9)"/>
      <circle cx="38" cy="16" r="10" fill="rgba(255,214,10,.9)"/>
      <path d="M47 15 L55 17 L47 20 Z" fill="rgba(255,122,0,.9)"/>
      <circle cx="41" cy="13" r="1.8" fill="#1e1b4b"/></svg>""",
    # paperclip with eyes
    """<svg width="40" height="60" viewBox="0 0 40 60" fill="none">
      <path d="M13 16 v26 a8 8 0 0 0 16 0 V12 a11 11 0 0 0 -22 0 v32" stroke="rgba(255,255,255,.8)" stroke-width="4" stroke-linecap="round" fill="none"/>
      <circle cx="17" cy="12" r="2.6" fill="#fff"/><circle cx="26" cy="12" r="2.6" fill="#fff"/>
      <circle cx="17.8" cy="12.6" r="1.2" fill="#1e1b4b"/><circle cx="26.8" cy="12.6" r="1.2" fill="#1e1b4b"/></svg>""",
    # friendly ghost
    """<svg width="48" height="56" viewBox="0 0 48 56" fill="none">
      <path d="M8 26 a16 16 0 0 1 32 0 v22 l-6 -5 -5 5 -5 -5 -5 5 -5 -5 -6 5 Z" fill="rgba(255,255,255,.75)"/>
      <circle cx="18" cy="24" r="3" fill="#1e1b4b"/><circle cx="30" cy="24" r="3" fill="#1e1b4b"/></svg>""",
    # tiny dino
    """<svg width="64" height="48" viewBox="0 0 64 48" fill="none">
      <path d="M44 10 h12 v8 h-6 v6 c0 10 -8 16 -18 16 h-4 l-4 6 -4 -6 h-6 c-6 0 -10 -6 -8 -12 l4 -12 c6 2 12 2 18 0 l4 -6 Z" fill="rgba(255,255,255,.75)"/>
      <circle cx="50" cy="15" r="2" fill="#1e1b4b"/></svg>""",
    # cat silhouette (generic)
    """<svg width="56" height="48" viewBox="0 0 56 48" fill="none">
      <path d="M12 44 c-4 -10 -2 -20 4 -26 l-2 -10 8 6 c4 -2 8 -2 12 0 l8 -6 -2 10 c6 6 8 16 4 26 Z" fill="rgba(255,255,255,.75)"/>
      <circle cx="22" cy="30" r="2.4" fill="#1e1b4b"/><circle cx="34" cy="30" r="2.4" fill="#1e1b4b"/>
      <path d="M26 36 q2 2 4 0" stroke="#1e1b4b" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>""",
]

# small text easter egg shown as a floating chip, rotated per tool
CHIPS = [
    "42 KB",
    "page 67 of 67",
    "much fast",
    "one more time",
    "level 67",
    "hello there",
]


def slug_of(path: str) -> str:
    return path.rstrip("/").replace("/", "-")


def pick_demo_files(accept: str, multiple: bool) -> list[Path]:
    exts = [
        a.strip().lower()
        for a in (accept or "").split(",")
        if a.strip().startswith(".")
    ]
    files: list[Path] = []
    for ext in exts:
        for name in DEMO_BY_EXT.get(ext, []):
            p = DEMO / name
            if p.exists() and p not in files:
                files.append(p)
    if not files:  # unknown/empty accept -> PDFs are the site's lingua franca
        files = [DEMO / n for n in DEMO_BY_EXT[".pdf"]]
    if not multiple:
        return files[:1]
    return files[:3]


def capture(page, path: str) -> bytes | None:
    slug = slug_of(path)
    try:
        page.goto(BASE + path, wait_until="networkidle", timeout=60000)
    except Exception as exc:
        print(f"  ! {slug}: load failed ({exc})", file=sys.stderr)
        return None
    # compact layout so headline + dropzone + staged file list all fit the crop
    page.add_style_tag(content="#cookie-banner{display:none !important} body{zoom:.85}")
    page.evaluate("window.scrollTo(0,0)")

    inputs = page.locator('input[type="file"]')
    staged = False
    staged_query = None  # text to find the rendered file row later
    # stage one input only: extra inputs are usually "replace file" /
    # signature-image pickers and staging them resets the tool state.
    # Prefer the input carrying `multiple` (merge exposes two dead single
    # inputs before the real multi one). compare-pdf needs both its inputs.
    total = inputs.count()
    if slug == "compare-pdf":
        order = list(range(min(total, 2)))
    else:
        order = [0] if total else []
        for i in range(total):
            if inputs.nth(i).get_attribute("multiple") is not None:
                order = [i]
                break
    for i in order:
        inp = inputs.nth(i)
        accept = inp.get_attribute("accept") or ""
        multiple = inp.get_attribute("multiple") is not None
        files = pick_demo_files(accept, multiple)
        try:
            inp.set_input_files([str(f) for f in files])
            staged = True
            if staged_query is None:
                staged_query = files[0].stem[:12]
        except Exception as exc:
            print(f"  ~ {slug}: input {i} staging failed ({exc})", file=sys.stderr)
    page.wait_for_timeout(5000 if slug in PREVIEW_TOOLS else 1200)
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(300)
    # anchor the crop just above the H1 (skips breadcrumbs, keeps the staged
    # file list in frame); preview tools anchor on their working panel heading
    # so the page-thumbnail grid is the star of the frame
    clip = dict(CLIP)
    anchor = None
    row = None
    if staged and staged_query:
        try:
            row = page.get_by_text(staged_query, exact=False).last.bounding_box()
        except Exception:
            row = None
    if slug in PREVIEW_TOOLS and row:
        # the staged-file row sits directly above the working panel
        anchor = row["y"] - 130
    else:
        try:
            h1 = page.locator("h1").first.bounding_box()
            if h1:
                anchor = h1["y"] - 90
        except Exception:
            anchor = None
        # keep the staged-file row fully inside the frame: end the crop just
        # below it when the H1-anchored window would cut it off
        if anchor is not None and row is not None:
            row_bottom = row["y"] + row["height"] + 28
            if row_bottom > anchor + CLIP["height"]:
                anchor = row_bottom - CLIP["height"]
    if anchor is not None:
        page_h = page.evaluate("document.documentElement.scrollHeight")
        clip["y"] = max(0, min(anchor, page_h - CLIP["height"] - 8))
    shot = page.screenshot(type="png", clip=clip, full_page=True)
    if not staged:
        print(f"  ~ {slug}: no file input (captured clean page)")
    return shot


def compose(page, raw_png: bytes, path: str, idx: int) -> bytes:
    b64 = base64.b64encode(raw_png).decode()
    g1, g2 = GRADIENTS[idx % len(GRADIENTS)]
    doodle_a = DOODLES[idx % len(DOODLES)]
    doodle_b = DOODLES[(idx + 3) % len(DOODLES)]
    chip = CHIPS[idx % len(CHIPS)]
    url_label = "convertica.net/" + path.rstrip("/")
    html = f"""<!doctype html><html><head><style>
      * {{ margin:0; box-sizing:border-box; }}
      body {{ width:1200px; height:750px; overflow:hidden;
             font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif; }}
      .bg {{ position:relative; width:1200px; height:750px;
            background:linear-gradient(135deg,{g1} 0%,{g2} 100%); }}
      .blob {{ position:absolute; border-radius:50%; filter:blur(70px); opacity:.5; }}
      .b1 {{ width:420px; height:420px; background:#fff; top:-160px; left:-120px; opacity:.16; }}
      .b2 {{ width:520px; height:520px; background:{g2}; bottom:-220px; right:-140px;
            filter:blur(90px); opacity:.55; }}
      .dots {{ position:absolute; inset:0;
        background-image:radial-gradient(rgba(255,255,255,.14) 1.5px, transparent 1.5px);
        background-size:26px 26px; }}
      .card {{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
        width:940px; border-radius:18px; overflow:hidden;
        box-shadow:0 30px 70px rgba(20,16,60,.45), 0 8px 24px rgba(20,16,60,.35); }}
      .chrome {{ height:44px; background:#eef2f7; display:flex; align-items:center;
        gap:8px; padding:0 16px; }}
      .dot {{ width:12px; height:12px; border-radius:50%; }}
      .url {{ flex:1; margin-left:10px; background:#fff; border-radius:8px; height:26px;
        display:flex; align-items:center; padding:0 12px; color:#475569; font-size:13px;
        font-weight:600; letter-spacing:.2px; }}
      .lock {{ margin-right:6px; font-size:11px; color:#16a34a; }}
      .shot {{ display:block; width:940px; }}
      .doodle {{ position:absolute; }}
      .d1 {{ left:38px; bottom:46px; transform:rotate(-8deg); }}
      .d2 {{ right:42px; top:52px; transform:rotate(10deg); }}
      .chip {{ position:absolute; right:96px; bottom:26px; z-index:3;
        background:rgba(255,255,255,.2); border:1px solid rgba(255,255,255,.45);
        backdrop-filter:blur(6px); color:#fff; white-space:nowrap;
        font-size:15px; font-weight:700; padding:7px 14px; border-radius:999px;
        box-shadow:0 6px 18px rgba(20,16,60,.35); }}
    </style></head><body>
      <div class="bg">
        <div class="dots"></div>
        <div class="blob b1"></div><div class="blob b2"></div>
        <div class="doodle d1">{doodle_a}</div>
        <div class="doodle d2">{doodle_b}</div>
        <div class="card">
          <div class="chrome">
            <div class="dot" style="background:#ff5f57"></div>
            <div class="dot" style="background:#febc2e"></div>
            <div class="dot" style="background:#28c840"></div>
            <div class="url"><span class="lock">&#128274;</span>{url_label}</div>
          </div>
          <img class="shot" src="data:image/png;base64,{b64}">
        </div>
        <div class="chip">{chip}</div>
      </div>
    </body></html>"""
    page.set_content(html)
    page.wait_for_timeout(150)
    return page.screenshot(
        type="png", clip={"x": 0, "y": 0, "width": 1200, "height": 750}
    )


def save_variants(png: bytes, slug: str) -> None:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img = img.resize((1200, 750), Image.LANCZOS) if img.size != (1200, 750) else img
    img.save(OUT / f"{slug}.jpg", quality=85, optimize=True)
    img.save(OUT / f"{slug}.webp", "WEBP", quality=82, method=6)
    card = img.resize((480, 300), Image.LANCZOS)
    card.save(OUT / f"{slug}-card.webp", "WEBP", quality=80, method=6)


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = argv or [slug_of(p) for p in TOOL_PATHS]
    paths = [p for p in TOOL_PATHS if slug_of(p) in set(wanted)]
    unknown = set(wanted) - {slug_of(p) for p in paths}
    if unknown:
        print(f"Unknown slug(s): {sorted(unknown)}", file=sys.stderr)
        return 1
    done = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        cap_page = browser.new_page(
            viewport={"width": 1280, "height": 900}, device_scale_factor=2
        )
        compose_page = browser.new_page(
            viewport={"width": 1200, "height": 750}, device_scale_factor=2
        )
        for idx, path in enumerate(paths):
            slug = slug_of(path)
            raw = capture(cap_page, path)
            if raw is None:
                continue
            final = compose(compose_page, raw, path, idx)
            save_variants(final, slug)
            done += 1
            print(f"  + {slug}")
        browser.close()
    print(f"Done: {done}/{len(paths)}")
    return 0 if done == len(paths) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
