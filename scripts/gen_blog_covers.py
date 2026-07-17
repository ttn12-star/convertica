#!/usr/bin/env python3
"""Generate branded 1200x630 blog cover images for Convertica.

Each article gets a distinct gradient + accent + inline SVG icon + kicker so no
two covers look alike. Output goes to ``static/blog/images/cover-<slug>.jpg``
(git-tracked, served from /static/). Re-run to regenerate; it is idempotent.

    python scripts/gen_blog_covers.py            # all covers
    python scripts/gen_blog_covers.py <slug> ... # only the given slugs

Requires Playwright chromium (already present in this environment).
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "static" / "blog" / "images"
LOGO = ROOT / "static" / "images" / "logo.png"

# --- inline SVG icons (Heroicons-style outline, 24x24 viewBox, stroke=white) ---
P = (
    'fill="none" stroke="white" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round"'
)
ICONS = {
    "compress": f'<path {P} d="M9 9 4 4m0 0v4m0-4h4m6 6 5 5m0 0v-4m0 4h-4M9 15l-5 5m0 0v-4m0 4h4m6-6 5-5m0 0v4m0-4h-4"/>',
    "doc": f'<path {P} d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z"/><path {P} d="M14 3v5h5M8 13h8M8 17h6"/>',
    "table": f'<rect {P} x="3" y="4" width="18" height="16" rx="2"/><path {P} d="M3 9h18M3 14.5h18M9 4v16M15 4v16"/>',
    "word": f'<rect {P} x="3" y="4" width="18" height="16" rx="2"/><path {P} d="m7 9 1.6 6L11 10.5 13.4 15 15 9"/>',
    "ocr": f'<path {P} d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><path {P} d="M8.5 15 12 8l3.5 7M9.7 12.5h4.6"/>',
    "lock": f'<rect {P} x="5" y="11" width="14" height="9" rx="2"/><path {P} d="M8 11V8a4 4 0 0 1 8 0v3M12 15v2"/>',
    "zip": f'<path {P} d="M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/><path {P} d="M12 3v3M12 8v2M12 12v2M10.5 15h3v3.5h-3z"/>',
    "merge": f'<path {P} d="M7 4v5a3 3 0 0 0 3 3h8m0 0-3-3m3 3-3 3M7 20v-5"/>',
    "tag": f'<path {P} d="M3 7a2 2 0 0 1 2-2h6l9 9a2 2 0 0 1 0 2.8l-4.2 4.2a2 2 0 0 1-2.8 0L4 12V7Z"/><circle {P} cx="8" cy="10" r="1.2"/>',
    "scale": f'<path {P} d="M12 4v16M6 8h12M6 8l-3 6a3 3 0 0 0 6 0L6 8Zm12 0-3 6a3 3 0 0 0 6 0l-3-6ZM8 20h8"/>',
    "pages": f'<rect {P} x="6" y="3" width="13" height="17" rx="2"/><path {P} d="M9 3v17" stroke-dasharray="2 2"/><path {P} d="M5 7v13a1 1 0 0 0 1 1h10"/>',
    "shuffle": f'<path {P} d="M4 7h3l9 10h4m0 0-3-3m3 3-3 3M4 17h3l3-3.3M16 7h4m0 0-3-3m3 3-3 3"/>',
    "rotate": f'<path {P} d="M4 12a8 8 0 1 1 2.3 5.6M4 19v-4h4"/>',
    "scissors": f'<circle {P} cx="6" cy="6" r="2.5"/><circle {P} cx="6" cy="18" r="2.5"/><path {P} d="M8 7.5 20 18M8 16.5 20 6"/>',
    "drop": f'<path {P} d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z"/><path {P} d="M9 14a3 3 0 0 0 3 3"/>',
    "pencil": f'<path {P} d="M4 20h4L19 9a2 2 0 0 0 0-2.8l-1.2-1.2a2 2 0 0 0-2.8 0L4 16v4Z"/><path {P} d="M13.5 6.5 17.5 10.5"/>',
    "image": f'<rect {P} x="3" y="5" width="18" height="14" rx="2"/><circle {P} cx="8.5" cy="10" r="1.5"/><path {P} d="m4 18 5-5 4 4 3-3 4 4"/>',
    "hash": f'<path {P} d="M9 4 7 20M17 4l-2 16M5 9h15M4 15h15"/>',
    "layers": f'<path {P} d="m12 3 9 5-9 5-9-5 9-5Z"/><path {P} d="m3 13 9 5 9-5M3 13l9 5 9-5"/>',
    "badge": f'<path {P} d="M12 3 4 6v6c0 4.4 3.4 7.6 8 9 4.6-1.4 8-4.6 8-9V6l-8-3Z"/><path {P} d="m9 12 2 2 4-4"/>',
    "rocket": f'<path {P} d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2a3 3 0 0 0-3-3Z"/><path {P} d="M9 11a16 16 0 0 1 8-8c2 0 3 1 3 3a16 16 0 0 1-8 8l-3-3Z"/><circle {P} cx="14.5" cy="9.5" r="1.3"/>',
    "star": f'<path {P} d="m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.9 6.6 19.5l1.2-6L3.3 9.3l6.1-.7L12 3Z"/>',
}

# --- per-article cover spec: (display title, kicker, gradient stops, accent, icon) ---
COVERS = {
    "compress-pdf-for-email-under-25mb": (
        "Compress a PDF\nfor Email",
        "PDF · EMAIL",
        ("#2563eb", "#06b6d4"),
        "#67e8f9",
        "compress",
    ),
    "convert-excel-to-pdf-keep-formatting": (
        "Excel to PDF,\nFormatting Intact",
        "EXCEL → PDF",
        ("#059669", "#0d9488"),
        "#6ee7b7",
        "table",
    ),
    "convert-scanned-pdf-to-editable-word": (
        "Scanned PDF to\nEditable Word",
        "OCR · WORD",
        ("#4338ca", "#2563eb"),
        "#a5b4fc",
        "word",
    ),
    "how-to-extract-text-from-an-image": (
        "Extract Text\nfrom an Image",
        "OCR · IMAGE",
        ("#a21caf", "#7c3aed"),
        "#f0abfc",
        "ocr",
    ),
    "how-to-password-protect-a-zip-file": (
        "Password-Protect\na ZIP File",
        "ZIP · SECURITY",
        ("#334155", "#2563eb"),
        "#93c5fd",
        "zip",
    ),
    "merge-invoices-into-one-pdf-for-accounting": (
        "Merge Invoices\ninto One PDF",
        "MERGE · PDF",
        ("#d97706", "#ea580c"),
        "#fcd34d",
        "merge",
    ),
    "password-protect-pdf-before-emailing": (
        "Password-Protect\na PDF",
        "PDF · SECURITY",
        ("#e11d48", "#be123c"),
        "#fda4af",
        "lock",
    ),
    "pdf-naming-conventions-best-practices": (
        "PDF Naming\nConventions",
        "BEST PRACTICES",
        ("#0891b2", "#0284c7"),
        "#7dd3fc",
        "tag",
    ),
    "pdf-to-word-vs-ocr-which-to-use": (
        "PDF to Word\nvs OCR",
        "COMPARISON",
        ("#7c3aed", "#4338ca"),
        "#c4b5fd",
        "scale",
    ),
    "remove-blank-pages-from-pdf": (
        "Remove Blank\nPages from PDF",
        "ORGANIZE PDF",
        ("#0d9488", "#059669"),
        "#5eead4",
        "pages",
    ),
    "reorder-pdf-pages-drag-and-drop": (
        "Reorder PDF\nPages",
        "ORGANIZE PDF",
        ("#2563eb", "#4338ca"),
        "#93c5fd",
        "shuffle",
    ),
    "rotate-pdf-pages-permanently": (
        "Rotate PDF\nPages for Good",
        "EDIT PDF",
        ("#ea580c", "#d97706"),
        "#fdba74",
        "rotate",
    ),
    "split-bank-statement-pdf-by-page": (
        "Split a PDF\nby Page",
        "SPLIT PDF",
        ("#0284c7", "#2563eb"),
        "#7dd3fc",
        "scissors",
    ),
    "watermark-pdf-confidential-draft": (
        'Add a "Confidential"\nWatermark',
        "WATERMARK",
        ("#db2777", "#e11d48"),
        "#fbcfe8",
        "drop",
    ),
    # new articles
    "edit-pdf-free-without-acrobat": (
        "Edit a PDF Free\nwithout Acrobat",
        "EDIT PDF",
        ("#7c3aed", "#c026d3"),
        "#e9d5ff",
        "pencil",
    ),
    "convert-pdf-to-jpg-and-back": (
        "Convert PDF to JPG\n(and Back)",
        "PDF ↔ JPG",
        ("#059669", "#16a34a"),
        "#86efac",
        "image",
    ),
    "add-page-numbers-to-pdf": (
        "Add Page Numbers\nto a PDF",
        "EDIT PDF",
        ("#4f46e5", "#7c3aed"),
        "#c7d2fe",
        "hash",
    ),
    "free-adobe-acrobat-alternatives-2026": (
        "Free Adobe Acrobat\nAlternatives",
        "COMPARISON · 2026",
        ("#b91c1c", "#7c3aed"),
        "#fca5a5",
        "badge",
    ),
    "combine-word-excel-jpg-into-one-pdf": (
        "Combine Files\ninto One PDF",
        "WORD · EXCEL · JPG",
        ("#0d9488", "#4338ca"),
        "#5eead4",
        "layers",
    ),
    # reconstructed orphan articles
    "complete-guide-pdf-to-word-conversion": (
        "PDF to Word:\nComplete Guide",
        "PDF → WORD",
        ("#4338ca", "#2563eb"),
        "#a5b4fc",
        "word",
    ),
    "ultimate-guide-pdf-compression-reduce-file-size": (
        "PDF Compression\nFull Guide",
        "COMPRESS PDF",
        ("#1d4ed8", "#0891b2"),
        "#67e8f9",
        "compress",
    ),
    "pdf-to-jpg-converter-online-free": (
        "PDF to JPG\nFree Online",
        "PDF → JPG",
        ("#059669", "#16a34a"),
        "#86efac",
        "image",
    ),
    "word-to-pdf-converter-online-free-2025": (
        "Word to PDF\nFree Online",
        "WORD → PDF",
        ("#4f46e5", "#7c3aed"),
        "#c7d2fe",
        "doc",
    ),
    "smallpdf-alternative-free-pdf-converter": (
        "Smallpdf\nAlternative",
        "COMPARISON",
        ("#7c3aed", "#2563eb"),
        "#c4b5fd",
        "scale",
    ),
    "ilovepdf-alternative-free-pdf-tools-2025": (
        "iLovePDF\nAlternative",
        "COMPARISON · 2025",
        ("#e11d48", "#db2777"),
        "#fbcfe8",
        "scale",
    ),
    "is-convertica-safe-pdf-file-security-privacy-explained": (
        "Is Convertica\nSafe?",
        "SECURITY · PRIVACY",
        ("#334155", "#2563eb"),
        "#93c5fd",
        "lock",
    ),
    "convertica-launch-update-testing-phase-upcoming-features": (
        "Launch Update &\nWhat's Coming",
        "PRODUCT NEWS",
        ("#0d9488", "#0284c7"),
        "#5eead4",
        "rocket",
    ),
    "convertica-major-release-premium-heroes-new-features-upgrades": (
        "Major Release:\nNew Features",
        "PRODUCT NEWS",
        ("#d97706", "#ea580c"),
        "#fcd34d",
        "star",
    ),
    "convert-heic-to-jpg-iphone-photos": (
        "HEIC to JPG:\niPhone Photos",
        "IMAGE · IPHONE",
        ("#0ea5e9", "#6366f1"),
        "#bae6fd",
        "image",
    ),
    "webp-vs-jpeg-vs-png-best-image-format": (
        "WebP vs JPEG\nvs PNG",
        "COMPARISON · WEB",
        ("#059669", "#0d9488"),
        "#a7f3d0",
        "scale",
    ),
    "convert-jpg-to-pdf-multiple-images": (
        "JPG to PDF:\nMany Images, One File",
        "PDF · IMAGE",
        ("#7c3aed", "#c026d3"),
        "#e9d5ff",
        "layers",
    ),
    "unlock-pdf-remove-password": (
        "Unlock a PDF,\nRemove a Password",
        "PDF · SECURITY",
        ("#334155", "#2563eb"),
        "#93c5fd",
        "lock",
    ),
    "pdf-to-excel-how-to": (
        "PDF to Excel:\nKeep Your Tables",
        "PDF → EXCEL",
        ("#059669", "#0d9488"),
        "#6ee7b7",
        "table",
    ),
    "sign-pdf-document-digitally": (
        "Sign a PDF\nWithout Printing",
        "EDIT PDF · SIGN",
        ("#4338ca", "#7c3aed"),
        "#c4b5fd",
        "pencil",
    ),
    "pdf-to-powerpoint-conversion": (
        "PDF to PowerPoint:\nEditable Slides",
        "PDF → PPT",
        ("#ea580c", "#db2777"),
        "#fdba74",
        "layers",
    ),
    "how-to-password-protect-a-photo": (
        "Password-Protect\na Photo",
        "IMAGE · SECURITY",
        ("#7c3aed", "#2563eb"),
        "#c4b5fd",
        "lock",
    ),
    "convertica-summer-2026-update-free-tools-background-tasks": (
        "Summer Update:\nMore Free Tools",
        "PRODUCT NEWS",
        ("#2563eb", "#7c3aed"),
        "#93c5fd",
        "rocket",
    ),
}

LOGO_B64 = base64.b64encode(LOGO.read_bytes()).decode()


def html_for(
    title: str, kicker: str, grad: tuple[str, str], accent: str, icon: str
) -> str:
    title_html = title.replace("\n", "<br>")
    c1, c2 = grad
    icon_svg = ICONS[icon]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:1200px; height:630px; overflow:hidden;
  font-family:'Segoe UI','DejaVu Sans','Liberation Sans',Arial,sans-serif; }}
.cover {{ width:1200px; height:630px; position:relative;
  background:linear-gradient(135deg,{c1} 0%,{c2} 100%); color:#fff;
  padding:64px 72px; display:flex; flex-direction:column; justify-content:space-between; }}
.blob {{ position:absolute; border-radius:50%; background:rgba(255,255,255,.08); }}
.b1 {{ width:520px; height:520px; right:-160px; top:-180px; }}
.b2 {{ width:300px; height:300px; right:120px; bottom:-120px; background:rgba(255,255,255,.06); }}
.brand {{ display:flex; align-items:center; gap:16px; position:relative; z-index:2; }}
.brand img {{ width:60px; height:60px; filter:drop-shadow(0 2px 6px rgba(0,0,0,.2)); }}
.brand .name {{ font-size:32px; font-weight:800; letter-spacing:-.5px; }}
.mid {{ position:relative; z-index:2; display:flex; align-items:center;
  justify-content:space-between; gap:40px; margin-top:8px; }}
.text {{ max-width:720px; }}
.kicker {{ display:inline-block; font-size:20px; font-weight:700; letter-spacing:3px;
  color:{accent}; margin-bottom:22px; }}
h1 {{ font-size:72px; line-height:1.05; font-weight:800; letter-spacing:-1.5px;
  text-shadow:0 2px 12px rgba(0,0,0,.18); }}
.accent-bar {{ width:120px; height:8px; border-radius:6px; background:{accent}; margin-top:28px; }}
.iconwrap {{ flex:0 0 auto; width:240px; height:240px; border-radius:40px;
  background:rgba(255,255,255,.14); border:2px solid rgba(255,255,255,.25);
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 20px 50px rgba(0,0,0,.18); backdrop-filter:blur(4px); }}
.iconwrap svg {{ width:150px; height:150px; }}
.foot {{ position:relative; z-index:2; display:flex; align-items:center;
  justify-content:space-between; font-size:24px; }}
.url {{ font-weight:700; opacity:.95; }}
.pill {{ background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.3);
  padding:12px 26px; border-radius:999px; font-weight:700; font-size:22px; }}
</style></head><body>
<div class="cover">
  <div class="blob b1"></div><div class="blob b2"></div>
  <div class="brand">
    <img src="data:image/png;base64,{LOGO_B64}" alt="">
    <span class="name">Convertica</span>
  </div>
  <div class="mid">
    <div class="text">
      <span class="kicker">{kicker}</span>
      <h1>{title_html}</h1>
      <div class="accent-bar"></div>
    </div>
    <div class="iconwrap"><svg viewBox="0 0 24 24">{icon_svg}</svg></div>
  </div>
  <div class="foot">
    <span class="url">convertica.net</span>
    <span class="pill">Free · No sign-up</span>
  </div>
</div></body></html>"""


def main(argv: list[str]) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slugs = argv or list(COVERS)
    unknown = [s for s in slugs if s not in COVERS]
    if unknown:
        print(f"Unknown slug(s): {unknown}", file=sys.stderr)
        return 1
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1200, "height": 630}, device_scale_factor=2
        )
        for slug in slugs:
            title, kicker, grad, accent, icon = COVERS[slug]
            page.set_content(
                html_for(title, kicker, grad, accent, icon), wait_until="networkidle"
            )
            out = OUT_DIR / f"cover-{slug}.jpg"
            page.locator(".cover").screenshot(path=str(out), type="jpeg", quality=88)
            print(f"  + {out.relative_to(ROOT)}")
        browser.close()
    print(f"Done: {len(slugs)} cover(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
