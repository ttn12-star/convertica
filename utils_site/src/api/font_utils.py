"""Shared Unicode font registration for reportlab-based PDF generation.

Several converters (watermark, page numbers, EPUB→PDF, OCR overlays) render
text with reportlab. reportlab's built-in Helvetica has no Cyrillic/Arabic/CJK
glyphs, so non-Latin text came out as blank boxes ("tofu") — a real problem for
the RU/AR audience. Registering a system Unicode TTF (DejaVu/Liberation/Noto)
once per process fixes it; the font also renders ASCII fine, so callers can use
it unconditionally.
"""

import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# (regular, bold) candidate pairs, in preference order. DejaVu covers
# Latin+Cyrillic+Greek; Noto/Liberation are fallbacks. Full Arabic/CJK/Devanagari
# coverage needs script-specific Noto faces in the image — see module note.
_UNICODE_FONT_PATHS = [
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ),
]

REGULAR_NAME = "UnicodeSans"
BOLD_NAME = "UnicodeSans-Bold"

# Cache the resolved (regular, bold) reportlab font names for the process.
_registered: tuple[str, str] | None = None


def unicode_font_file() -> str | None:
    """Path to a regular Unicode TTF on disk, or None (for fitz/PyMuPDF callers)."""
    for regular, _bold in _UNICODE_FONT_PATHS:
        if os.path.exists(regular):
            return regular
    return None


def register_unicode_font() -> tuple[str, str]:
    """Register a Unicode TTF with reportlab; return (regular, bold) font names.

    Falls back to ("Helvetica", "Helvetica-Bold") if no system TTF is found, so
    callers can always use the returned names without extra branching. Idempotent
    and cached — reportlab font registration is global to the process.
    """
    global _registered
    if _registered is not None:
        return _registered

    for regular_path, bold_path in _UNICODE_FONT_PATHS:
        if not os.path.exists(regular_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(REGULAR_NAME, regular_path))
            bold_path = bold_path if os.path.exists(bold_path) else regular_path
            pdfmetrics.registerFont(TTFont(BOLD_NAME, bold_path))
            _registered = (REGULAR_NAME, BOLD_NAME)
            return _registered
        except Exception:
            continue

    _registered = ("Helvetica", "Helvetica-Bold")
    return _registered


if __name__ == "__main__":
    # Smoke check: resolves to a real TTF on a machine that has DejaVu, else
    # falls back cleanly to Helvetica without raising.
    reg, bold = register_unicode_font()
    assert reg and bold, "font names must be non-empty"
    assert register_unicode_font() == (reg, bold), "must be cached/idempotent"
    print("register_unicode_font ->", (reg, bold), "| file:", unicode_font_file())
