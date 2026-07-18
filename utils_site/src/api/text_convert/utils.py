"""
Text to PDF conversion utilities.

The user pastes plain text plus a few global style options; we wrap the text in
a small, fully-escaped HTML document and hand it to the existing Playwright
HTML->PDF converter. Reusing that pipeline gives us correct rendering of every
script (Arabic/RTL, Hindi, CJK, Cyrillic) for free and avoids a second PDF
engine on the box.
"""

import html

# Global style option -> CSS. Kept server-side (not trusting client CSS) so a
# hostile payload can only pick from these fixed values.
FONT_STACKS = {
    # Chromium falls back to the matching Noto face per script automatically,
    # so a single generic family covers all 7 site languages.
    "sans": '"Noto Sans", "Noto Sans Arabic", "Noto Sans Devanagari", sans-serif',
    "serif": '"Noto Serif", "Noto Serif Arabic", "Noto Serif Devanagari", serif',
    "mono": '"Noto Sans Mono", "Courier New", monospace',
}

ALIGNMENTS = {"left", "right", "center", "justify"}

# Margin preset -> physical margin passed to Playwright's pdf().
MARGIN_PRESETS = {
    "narrow": "1cm",
    "normal": "2cm",
    "wide": "3cm",
}


def build_html(
    text: str,
    *,
    font: str = "sans",
    font_size: int = 12,
    color: str = "#111111",
    align: str = "left",
) -> str:
    """Wrap plain text in a safe, styled HTML document.

    The text is HTML-escaped so any `<`, `>`, `&` the user pasted renders as
    literal characters instead of markup (this is the injection guard). We use
    `white-space: pre-wrap` so newlines, blank lines, and runs of spaces are
    preserved exactly without hand-rolling <br> conversion. `dir="auto"` lets
    the browser infer paragraph direction, so pasted Arabic/Hebrew reads RTL.
    """
    font_family = FONT_STACKS.get(font, FONT_STACKS["sans"])
    if align not in ALIGNMENTS:
        align = "left"
    escaped = html.escape(text)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>"
        f"body{{margin:0;font-family:{font_family};font-size:{font_size}pt;"
        f"color:{color};text-align:{align};line-height:1.5;"
        "white-space:pre-wrap;word-wrap:break-word;overflow-wrap:break-word;}}"
        "</style></head>"
        f"<body dir='auto'>{escaped}</body></html>"
    )


def convert_text_to_pdf(
    text: str,
    *,
    font: str = "sans",
    font_size: int = 12,
    color: str = "#111111",
    align: str = "left",
    page_size: str = "A4",
    margin: str = "normal",
    filename: str = "document",
) -> tuple[str, str]:
    """Build styled HTML from `text` and render it to PDF via the shared engine.

    Returns (input_html_path, output_pdf_path) exactly like convert_html_to_pdf.
    """
    # Imported lazily so this module (and its __main__ check) loads without the
    # Playwright import chain / Django settings.
    from src.api.html_convert.utils import convert_html_to_pdf

    doc = build_html(text, font=font, font_size=font_size, color=color, align=align)
    margin_cm = MARGIN_PRESETS.get(margin, MARGIN_PRESETS["normal"])
    return convert_html_to_pdf(
        doc,
        filename=filename,
        suffix="_convertica",
        format=page_size,
        margin={
            "top": margin_cm,
            "bottom": margin_cm,
            "left": margin_cm,
            "right": margin_cm,
        },
    )


if __name__ == "__main__":
    # Smallest thing that breaks if the injection guard or whitespace handling
    # regresses. No framework — run directly.
    out = build_html("a < b & c >\n  spaced", font="serif", font_size=14)
    assert "&lt; b &amp; c &gt;" in out, out
    assert "<script" not in out.lower()
    assert "pre-wrap" in out
    assert "14pt" in out
    assert build_html("x", align="drop table").count("text-align:left") == 1
    print("build_html OK")
