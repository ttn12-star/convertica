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
    "image/password-protect-image/",
]

# demo file per extension; multi-file tools get the list
DEMO_BY_EXT = {
    ".pdf": [
        "plan_to_defeat_titans_v2_FINAL.pdf",
        "chapter_67_storyboard.pdf",
        "hallelujah_chords.pdf",
        "voyager_golden_record_tracklist.pdf",
        "principia_notes_draft.pdf",
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

# per-slug demo file override: takes priority over the extension pool above,
# so a tool always gets its bespoke prop regardless of idx rotation when the
# generator is run for a subset of slugs (as the regen recipe does).
DEMO_OVERRIDES = {
    "image-password-protect-image": ["project_nightingale_dossier.jpg"],
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

# gradient palette keyed by tool category (URL prefix) — each category gets
# its own hue family so the set reads varied-but-systematic; index rotates
# within the family for extra variety.
GRADIENTS_BY_CATEGORY = {
    "convert": [  # top-level converters: brand blues/violets
        ("#4f46e5", "#7c3aed"),
        ("#2563eb", "#7c3aed"),
        ("#1d4ed8", "#8b5cf6"),
        ("#4338ca", "#9333ea"),
    ],
    "pdf-edit": [  # editing: deep violets/fuchsia
        ("#7c3aed", "#c026d3"),
        ("#6d28d9", "#db2777"),
        ("#9333ea", "#e879f9"),
    ],
    "pdf-organize": [  # organizing: teal/cyan
        ("#0d9488", "#0891b2"),
        ("#0e7490", "#2563eb"),
        ("#059669", "#06b6d4"),
    ],
    "pdf-security": [  # security: emerald/green
        ("#059669", "#16a34a"),
        ("#047857", "#65a30d"),
    ],
    "image": [  # image tools: warm sunset
        ("#ea580c", "#e11d48"),
        ("#f59e0b", "#ef4444"),
        ("#e11d48", "#a21caf"),
        ("#d97706", "#db2777"),
    ],
    "archive": [  # archives: amber/bronze
        ("#b45309", "#92400e"),
        ("#d97706", "#b91c1c"),
    ],
}


def gradient_for(path: str, idx: int) -> tuple[str, str]:
    family = GRADIENTS_BY_CATEGORY.get(
        path.split("/")[0], GRADIENTS_BY_CATEGORY["convert"]
    )
    return family[idx % len(family)]


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
    # pixel heart
    """<svg width="44" height="40" viewBox="0 0 44 40" fill="none">
      <path d="M6 6h8v4h4v4h8V10h4V6h8v8h-4v4h-4v4h-4v4h-4v4h-4v-4h-4v-4h-4v-4H6v-4H2V6h4Z" fill="rgba(255,255,255,.8)"/></svg>""",
    # little UFO with beam
    """<svg width="60" height="56" viewBox="0 0 60 56" fill="none">
      <ellipse cx="30" cy="18" rx="22" ry="8" fill="rgba(255,255,255,.8)"/>
      <ellipse cx="30" cy="12" rx="10" ry="7" fill="rgba(255,255,255,.55)"/>
      <path d="M22 24 L16 52 H44 L38 24 Z" fill="rgba(255,255,255,.18)"/>
      <circle cx="18" cy="18" r="2" fill="#1e1b4b"/><circle cx="30" cy="20" r="2" fill="#1e1b4b"/><circle cx="42" cy="18" r="2" fill="#1e1b4b"/></svg>""",
    # coffee cup with steam
    """<svg width="44" height="52" viewBox="0 0 44 52" fill="none">
      <path d="M10 20 h22 v14 a10 10 0 0 1 -10 10 h-2 a10 10 0 0 1 -10 -10 Z" fill="rgba(255,255,255,.8)"/>
      <path d="M32 24 h4 a5 5 0 0 1 0 10 h-4" stroke="rgba(255,255,255,.8)" stroke-width="3" fill="none"/>
      <path d="M17 6 q3 4 0 8 M25 4 q3 5 0 10" stroke="rgba(255,255,255,.6)" stroke-width="2.5" fill="none" stroke-linecap="round"/></svg>""",
    # ringed planet
    """<svg width="64" height="52" viewBox="0 0 64 52" fill="none">
      <circle cx="32" cy="26" r="14" fill="rgba(255,255,255,.8)"/>
      <ellipse cx="32" cy="28" rx="28" ry="8" stroke="rgba(255,255,255,.7)" stroke-width="3" fill="none" transform="rotate(-14 32 28)"/>
      <circle cx="27" cy="22" r="2.5" fill="rgba(30,27,75,.35)"/><circle cx="37" cy="30" r="3.5" fill="rgba(30,27,75,.25)"/></svg>""",
    # little rocket
    """<svg width="44" height="60" viewBox="0 0 44 60" fill="none">
      <path d="M22 2 c8 8 10 20 6 32 h-12 c-4 -12 -2 -24 6 -32 Z" fill="rgba(255,255,255,.85)"/>
      <circle cx="22" cy="20" r="4.5" fill="rgba(30,27,75,.6)"/>
      <path d="M16 34 l-8 10 8 -2 Z M28 34 l8 10 -8 -2 Z" fill="rgba(255,255,255,.6)"/>
      <path d="M20 44 q2 8 2 12 q0 -4 2 -12" stroke="rgba(255,214,10,.9)" stroke-width="3" fill="none" stroke-linecap="round"/></svg>""",
    # telescope
    """<svg width="60" height="52" viewBox="0 0 60 52" fill="none">
      <rect x="8" y="14" width="36" height="10" rx="5" fill="rgba(255,255,255,.8)" transform="rotate(-18 26 19)"/>
      <path d="M26 26 L18 48 M28 26 L36 48" stroke="rgba(255,255,255,.7)" stroke-width="3" stroke-linecap="round"/>
      <circle cx="52" cy="8" r="2" fill="#fff"/><circle cx="44" cy="4" r="1.4" fill="rgba(255,255,255,.7)"/></svg>""",
    # atom
    """<svg width="56" height="56" viewBox="0 0 56 56" fill="none">
      <ellipse cx="28" cy="28" rx="24" ry="9" stroke="rgba(255,255,255,.7)" stroke-width="2.5" fill="none"/>
      <ellipse cx="28" cy="28" rx="24" ry="9" stroke="rgba(255,255,255,.7)" stroke-width="2.5" fill="none" transform="rotate(60 28 28)"/>
      <ellipse cx="28" cy="28" rx="24" ry="9" stroke="rgba(255,255,255,.7)" stroke-width="2.5" fill="none" transform="rotate(120 28 28)"/>
      <circle cx="28" cy="28" r="4" fill="rgba(255,214,10,.95)"/></svg>""",
    # lab flask
    """<svg width="44" height="56" viewBox="0 0 44 56" fill="none">
      <path d="M18 4 h8 v16 l10 24 a5 5 0 0 1 -5 8 H13 a5 5 0 0 1 -5 -8 l10 -24 Z" fill="rgba(255,255,255,.8)"/>
      <path d="M12 38 h20 l4 8 a4 4 0 0 1 -4 6 H12 a4 4 0 0 1 -4 -6 Z" fill="rgba(124,58,237,.55)"/>
      <circle cx="20" cy="42" r="2" fill="#fff"/><circle cx="27" cy="46" r="1.5" fill="#fff"/></svg>""",
]

# small text easter egg shown as a floating chip, rotated per tool
CHIPS = [
    "42 KB",
    "page 67 of 67",
    "much fast",
    "one more time",
    "level 67",
    "hello there",
    "no watermarks, only vibes",
    "6 to 7 seconds",
    "achievement unlocked",
    "it's dangerous to convert alone",
    "42 — the answer",
    "E = mc\u00b2 approved",
    "houston, no problems found",
    "one small step for PDF",
    "may the files be with you",
    "elementary, my dear PDF",
    "eureka!",
    "second star to the right",
    "per aspera ad PDF",
    "great scott, that was fast",
]


# per-tool conversion badge: "PDF -> DOCX" for converters, action word otherwise
FMT = {
    "pdf": "PDF",
    "word": "DOCX",
    "jpg": "JPG",
    "excel": "XLSX",
    "ppt": "PPTX",
    "html": "HTML",
    "markdown": "MD",
    "text": "TXT",
    "epub": "EPUB",
    "heic": "HEIC",
    "png": "PNG",
    "svg": "SVG",
    "webp": "WEBP",
    "ico": "ICO",
}
BADGE_OVERRIDES = {
    "compare-pdf": ("PDF", "PDF"),
    "scanned-pdf-to-word": ("SCAN", "DOCX"),
    "image-to-text": ("IMG", "TXT"),
    "image-convert": ("IMG", "ANY"),
    "image-optimize": ("OPTIMIZE",),
    "image-favicon-generator": ("FAVICON",),
    "image-password-protect-image": ("IMG", "\U0001f512PDF"),
}


def badge_parts(slug: str) -> tuple[str, ...]:
    if slug in BADGE_OVERRIDES:
        return BADGE_OVERRIDES[slug]
    last = slug.split("-")
    if "to" in last:
        i = last.index("to")
        a = FMT.get("-".join(last[:i]).split("-")[-1], last[i - 1].upper())
        b = FMT.get(last[i + 1], last[i + 1].upper())
        return (a, b)
    action = slug.rsplit("-", 1)[-1] if slug.count("-") else slug
    words = {
        "merge": "MERGE",
        "split": "SPLIT",
        "compress": "COMPRESS",
        "rotate": "ROTATE",
        "crop": "CROP",
        "flatten": "FLATTEN",
        "sign": "SIGN",
        "organize": "REORDER",
        "pages": "PAGES",
        "watermark": "WATERMARK",
        "numbers": "PAGE No",
        "protect": "PROTECT",
        "unlock": "UNLOCK",
        "remove": "REMOVE",
        "extract": "EXTRACT",
    }
    for key in reversed(slug.split("-")):
        if key in words:
            return (words[key],)
    return (action.upper(),)


def slug_of(path: str) -> str:
    return path.rstrip("/").replace("/", "-")


def pick_demo_files(
    accept: str, multiple: bool, idx: int = 0, slug: str | None = None
) -> list[Path]:
    if slug in DEMO_OVERRIDES:
        override = [DEMO / n for n in DEMO_OVERRIDES[slug] if (DEMO / n).exists()]
        if override:
            return override if multiple else override[:1]
    exts = [
        a.strip().lower()
        for a in (accept or "").split(",")
        if a.strip().startswith(".")
    ]
    files: list[Path] = []
    for ext in exts:
        pool = DEMO_BY_EXT.get(ext, [])
        pool = pool[idx % len(pool) :] + pool[: idx % len(pool)] if pool else pool
        for name in pool:
            p = DEMO / name
            if p.exists() and p not in files:
                files.append(p)
    if not files:  # unknown/empty accept -> PDFs are the site's lingua franca
        pool = DEMO_BY_EXT[".pdf"]
        pool = pool[idx % len(pool) :] + pool[: idx % len(pool)]
        files = [DEMO / n for n in pool]
    if not multiple:
        return files[:1]
    return files[:3]


def capture(page, path: str, idx: int = 0) -> bytes | None:
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
        files = pick_demo_files(accept, multiple, idx, slug)
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
    g1, g2 = gradient_for(path, idx)
    doodle_a = DOODLES[idx % len(DOODLES)]
    doodle_b = DOODLES[(idx + 3) % len(DOODLES)]
    chip = CHIPS[idx % len(CHIPS)]
    tilt = (-1.2, 0.0, 1.2)[idx % 3]
    # three blob layouts so backgrounds don't all share the same geometry
    blob_css = (
        ".b1 { width:420px; height:420px; background:#fff; top:-160px; left:-120px; opacity:.16; }"
        " .b2 { width:520px; height:520px; bottom:-220px; right:-140px; filter:blur(90px); opacity:.55; }",
        ".b1 { width:360px; height:360px; background:#fff; bottom:-140px; left:-100px; opacity:.14; }"
        " .b2 { width:560px; height:560px; top:-260px; right:-160px; filter:blur(95px); opacity:.5; }",
        ".b1 { width:300px; height:300px; background:#fff; top:40%; left:-160px; opacity:.15; }"
        " .b2 { width:480px; height:480px; bottom:-200px; right:30%; filter:blur(90px); opacity:.45; }",
    )[idx % 3]
    url_label = "convertica.net/" + path.rstrip("/")
    parts = badge_parts(slug_of(path))
    if len(parts) == 2:
        badge_html = (
            f'<span class="pill">{parts[0]}</span>'
            '<span class="barrow">&#10142;</span>'
            f'<span class="pill">{parts[1]}</span>'
        )
    else:
        badge_html = f'<span class="pill">{parts[0]}</span>'
    html = f"""<!doctype html><html><head><style>
      * {{ margin:0; box-sizing:border-box; }}
      body {{ width:1200px; height:750px; overflow:hidden;
             font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif; }}
      .bg {{ position:relative; width:1200px; height:750px;
            background:linear-gradient(135deg,{g1} 0%,{g2} 100%); }}
      .blob {{ position:absolute; border-radius:50%; filter:blur(70px); opacity:.5; }}
      .b2 {{ background:{g2}; }}
      {blob_css}
      .dots {{ position:absolute; inset:0;
        background-image:radial-gradient(rgba(255,255,255,.14) 1.5px, transparent 1.5px);
        background-size:26px 26px; }}
      .card {{ position:absolute; left:50%; top:50%;
        transform:translate(-50%,-50%) rotate({tilt}deg);
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
        background:rgba(15,23,42,.55); border:1px solid rgba(255,255,255,.35);
        backdrop-filter:blur(6px); color:#fff; white-space:nowrap;
        font-size:15px; font-weight:700; padding:7px 14px; border-radius:999px;
        box-shadow:0 6px 18px rgba(20,16,60,.35); }}
      .badge {{ position:absolute; left:88px; top:22px; z-index:4;
        display:flex; align-items:center; gap:10px; transform:rotate(-2deg); }}
      .badge .pill {{ background:#fff; color:{g1}; font-weight:800; font-size:21px;
        letter-spacing:.05em; padding:9px 16px; border-radius:13px;
        box-shadow:0 10px 26px rgba(15,10,50,.35); }}
      .badge .barrow {{ color:#fff; font-size:26px;
        text-shadow:0 2px 10px rgba(15,10,50,.4); }}
    </style></head><body>
      <div class="bg">
        <div class="dots"></div>
        <div class="blob b1"></div><div class="blob b2"></div>
        <div class="badge">{badge_html}</div>\n        <div class="doodle d1">{doodle_a}</div>
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
            raw = capture(cap_page, path, idx)
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
