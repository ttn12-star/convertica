"""Shared Unicode font handling for reportlab/fitz-based PDF generation.

reportlab's built-in Helvetica has no Cyrillic/Arabic/CJK/Devanagari glyphs, so
non-Latin text came out as blank boxes ("tofu"). A single TTF can't cover every
script, so we detect the dominant script of the text and register the matching
system Noto face (DejaVu for Latin/Cyrillic). Arabic additionally needs shaping
(contextual joining + RTL reordering), which reportlab can't do on its own — we
run arabic-reshaper + python-bidi first.

All font files are shipped in the image (fonts-dejavu-core, fonts-noto-core,
fonts-noto-cjk). If a face or the shaping libs are missing we fall back to
DejaVu / raw text, so callers can use these helpers unconditionally.
"""

import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Per-script font faces: script -> (regular_path, bold_path, ttc_subfont_index).
# ttc index is None for plain .ttf; CJK ships as a .ttc collection.
_FACES = {
    "arabic": (
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        None,
    ),
    "devanagari": (
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        None,
    ),
    "cjk": (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        0,
    ),
    # Latin + Cyrillic + Greek. Also the fallback for anything unrecognised.
    "default": (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        None,
    ),
}

# Extra DejaVu search locations (dev machines / non-Debian layouts).
_DEJAVU_FALLBACKS = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
)

# Resolved reportlab font names per script, cached for the process.
_registered: dict[str, tuple[str, str]] = {}


def detect_script(text: str, sample: int = 4000) -> str:
    """Return the dominant non-Latin script key in ``text`` (else "default").

    Latin/Cyrillic/digits all map to "default" (DejaVu handles them). We only
    switch faces when Arabic/Devanagari/CJK characters dominate the sample.
    """
    counts = {"arabic": 0, "devanagari": 0, "cjk": 0}
    for ch in text[:sample]:
        o = ord(ch)
        if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0xFB50 <= o <= 0xFEFF:
            counts["arabic"] += 1
        elif 0x0900 <= o <= 0x097F:
            counts["devanagari"] += 1
        elif (
            0x4E00 <= o <= 0x9FFF  # CJK unified
            or 0x3040 <= o <= 0x30FF  # kana
            or 0xAC00 <= o <= 0xD7AF  # hangul
        ):
            counts["cjk"] += 1
    script = max(counts, key=counts.get)
    return script if counts[script] > 0 else "default"


def _resolve_default_paths() -> tuple[str, str, None]:
    reg, bold, _ = _FACES["default"]
    if os.path.exists(reg):
        return reg, bold, None
    for alt in _DEJAVU_FALLBACKS:
        if os.path.exists(alt):
            return alt, alt, None
    return reg, bold, None  # may not exist -> register falls back to Helvetica


def register_font_for_script(script: str) -> tuple[str, str]:
    """Register the face for ``script`` with reportlab; return (regular, bold)
    font names. Falls back to DejaVu then Helvetica. Idempotent + cached."""
    if script in _registered:
        return _registered[script]

    reg_path, bold_path, ttc = _FACES.get(script, _FACES["default"])
    if script == "default" or not os.path.exists(reg_path):
        reg_path, bold_path, ttc = _resolve_default_paths()
        script_key = "default"
    else:
        script_key = script

    reg_name = f"U-{script_key}"
    bold_name = f"U-{script_key}-Bold"
    try:
        if ttc is not None:
            pdfmetrics.registerFont(TTFont(reg_name, reg_path, subfontIndex=ttc))
            bold_src = bold_path if os.path.exists(bold_path) else reg_path
            pdfmetrics.registerFont(TTFont(bold_name, bold_src, subfontIndex=ttc))
        else:
            pdfmetrics.registerFont(TTFont(reg_name, reg_path))
            bold_src = bold_path if os.path.exists(bold_path) else reg_path
            pdfmetrics.registerFont(TTFont(bold_name, bold_src))
        result = (reg_name, bold_name)
    except Exception:
        result = ("Helvetica", "Helvetica-Bold")

    _registered[script] = result
    return result


def register_unicode_font_for_text(text: str) -> tuple[str, str]:
    """Pick + register the reportlab font matching ``text``'s dominant script."""
    return register_font_for_script(detect_script(text or ""))


def register_unicode_font() -> tuple[str, str]:
    """Default Latin/Cyrillic (DejaVu) font names — for callers with no text
    to inspect (e.g. page numbers)."""
    return register_font_for_script("default")


def unicode_font_file(text: str | None = None) -> str | None:
    """Path to the TTF matching ``text``'s script (for fitz/PyMuPDF callers).

    .ttc collections (CJK) are skipped — fitz insert_textbox wants a plain file;
    callers needing CJK should use fitz's built-in CJK fonts instead.
    """
    script = detect_script(text or "") if text else "default"
    reg_path, _bold, ttc = _FACES.get(script, _FACES["default"])
    if ttc is None and os.path.exists(reg_path):
        return reg_path
    reg_path, _bold, _ = _resolve_default_paths()
    return reg_path if os.path.exists(reg_path) else None


def shape_rtl(text: str) -> str:
    """Reshape + reorder Arabic text so reportlab (no shaping engine) renders it
    with joined contextual forms in correct visual order. No-op for non-Arabic
    or if the shaping libraries aren't installed."""
    if detect_script(text) != "arabic":
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


if __name__ == "__main__":
    # Smoke check: script detection + registration fall back cleanly.
    assert detect_script("Привет мир") == "default"
    assert detect_script("مرحبا بالعالم") == "arabic"
    assert detect_script("नमस्ते दुनिया") == "devanagari"
    assert detect_script("こんにちは世界") == "cjk"
    reg, bold = register_unicode_font()
    assert reg and bold
    assert register_unicode_font_for_text("مرحبا")  # no raise
    print("font_utils OK:", {s: register_font_for_script(s) for s in _FACES})
    print("shape_rtl(arabic) changed:", shape_rtl("مرحبا") != "مرحبا")
