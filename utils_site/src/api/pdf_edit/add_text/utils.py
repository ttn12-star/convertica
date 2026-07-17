# utils.py
"""Materialize add-text operations into a PDF via PyMuPDF.

Text goes in as real, selectable text through `insert_htmlbox` with
bundled Noto fonts (Latin/Cyrillic out of the box; Arabic and Devanagari
are auto-detected per box and rendered with the matching Noto script
font — mupdf's built-in HarfBuzz does the shaping, verified in the
2026-07-17 spike). Whiteout/highlight are vector rectangles drawn on top
of the page content in array order, so later objects cover earlier ones
exactly like in the browser preview.

Whiteout is a visual cover-up, NOT redaction: the original content stays
in the file underneath. The landing-page FAQ says so explicitly.
"""
import html
import os
import re

import fitz  # PyMuPDF
from django.core.files.uploadedfile import UploadedFile
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

# family key -> @font-face css name
_FAMILY_CSS = """
@font-face {font-family: sans; src: url(NotoSans-Regular.ttf);}
@font-face {font-family: sans; src: url(NotoSans-Bold.ttf); font-weight: bold;}
@font-face {font-family: sans; src: url(NotoSans-Italic.ttf); font-style: italic;}
@font-face {font-family: sans; src: url(NotoSans-BoldItalic.ttf); font-weight: bold; font-style: italic;}
@font-face {font-family: serif2; src: url(NotoSerif-Regular.ttf);}
@font-face {font-family: serif2; src: url(NotoSerif-Bold.ttf); font-weight: bold;}
@font-face {font-family: mono; src: url(NotoSansMono-Regular.ttf);}
@font-face {font-family: mono; src: url(NotoSansMono-Bold.ttf); font-weight: bold;}
@font-face {font-family: arabic; src: url(NotoNaskhArabic-Regular.ttf);}
@font-face {font-family: deva; src: url(NotoSansDevanagari-Regular.ttf);}
"""

_FAMILY_BY_KEY = {"sans": "sans", "serif": "serif2", "mono": "mono"}

_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Typographic characters missing from some Noto script fonts -> safe ASCII.
_CHAR_FALLBACK = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    " ": " ",
}

_SCRIPT_FONT_FILES = {
    "arabic": "NotoNaskhArabic-Regular.ttf",
    "deva": "NotoSansDevanagari-Regular.ttf",
}
_script_fonts_cache: dict[str, fitz.Font] = {}


def _script_font(family: str) -> fitz.Font | None:
    if family not in _SCRIPT_FONT_FILES:
        return None
    if family not in _script_fonts_cache:
        _script_fonts_cache[family] = fitz.Font(
            fontfile=os.path.join(FONTS_DIR, _SCRIPT_FONT_FILES[family])
        )
    return _script_fonts_cache[family]


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _pick_family(text: str, font_key: str) -> tuple[str, bool]:
    """Choose css family by script content; returns (family, is_rtl)."""
    if _ARABIC_RE.search(text):
        return "arabic", True
    if _DEVANAGARI_RE.search(text):
        return "deva", False
    return _FAMILY_BY_KEY.get(font_key, "sans"), False


def _sanitize_for_font(text: str, family: str) -> str:
    """Replace typographic chars the script font lacks with ASCII lookalikes."""
    font = _script_font(family)
    if font is None:
        return text
    out = []
    for ch in text:
        if ch in _CHAR_FALLBACK and not font.has_glyph(ord(ch)):
            out.append(_CHAR_FALLBACK[ch])
        else:
            out.append(ch)
    return "".join(out)


def _text_op_html(op: dict) -> str:
    """Build the html + inline css for one text operation."""
    family, rtl = _pick_family(op["text"], op.get("font_key", "sans"))
    text = _sanitize_for_font(op["text"], family)
    body = html.escape(text).replace("\r\n", "\n").replace("\n", "<br>")

    styles = [
        f"font-family: {family}",
        f"font-size: {op.get('font_size', 14):g}px",
        f"color: {op.get('color', '#111111')}",
        f"text-align: {op.get('align', 'left')}",
        "margin: 0",
    ]
    if op.get("bold"):
        styles.append("font-weight: bold")
    if op.get("italic"):
        styles.append("font-style: italic")
    if op.get("underline"):
        styles.append("text-decoration: underline")
    if rtl:
        styles.append("direction: rtl")
        if op.get("align", "left") == "left":
            # RTL text left-aligned looks broken; follow the reading direction.
            styles[3] = "text-align: right"

    return f'<p style="{"; ".join(styles)}">{body}</p>'


def _clamp_rect(page: fitz.Page, op: dict) -> fitz.Rect:
    """Clamp an operation rect inside the page (same contract as sign_pdf)."""
    page_w = page.rect.width
    page_h = page.rect.height
    x = max(0.0, min(float(op["x"]), page_w - 1))
    y = max(0.0, min(float(op["y"]), page_h - 1))
    w = max(4.0, min(float(op["width"]), page_w - x))
    h = max(4.0, min(float(op["height"]), page_h - y))
    return fitz.Rect(x, y, x + w, y + h)


def add_text_pdf(
    pdf_file: UploadedFile,
    operations: list[dict],
    suffix: str = "_edited",
) -> tuple[str, str]:
    """Apply a list of text/whiteout/highlight operations to a PDF.

    Args:
        pdf_file: The uploaded PDF file.
        operations: Validated operation dicts (see OperationItemSerializer).
        suffix: Output filename suffix.

    Returns:
        Tuple of (input_pdf_path, output_pdf_path).

    Raises:
        ConversionError on processing failure.
    """
    context = {
        "function": "add_text_pdf",
        "input_filename": os.path.basename(pdf_file.name),
        "input_size": pdf_file.size,
        "operation_count": len(operations),
    }

    try:
        processor = BasePDFProcessor(
            pdf_file,
            tmp_prefix="add_text_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()
        tmp_dir = processor.tmp_dir

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(tmp_dir, f"{base}{suffix}.pdf")
        context["output_path"] = output_path

        archive = fitz.Archive(FONTS_DIR)
        doc = fitz.open(pdf_path)
        try:
            total_pages = len(doc)
            context["total_pages"] = total_pages
            has_text_ops = False

            for op in operations:
                page = doc[max(0, min(int(op["page"]), total_pages - 1))]
                rect = _clamp_rect(page, op)

                if op["type"] == "text":
                    has_text_ops = True
                    page.insert_htmlbox(
                        rect,
                        _text_op_html(op),
                        css=_FAMILY_CSS,
                        archive=archive,
                    )
                elif op["type"] == "whiteout":
                    page.draw_rect(
                        rect,
                        color=None,
                        fill=_hex_to_rgb(op.get("color", "#ffffff")),
                        overlay=True,
                    )
                else:  # highlight
                    page.draw_rect(
                        rect,
                        color=None,
                        fill=_hex_to_rgb(op.get("color", "#ffee00")),
                        fill_opacity=0.4,
                        overlay=True,
                    )

            if has_text_ops:
                doc.subset_fonts()
            doc.save(output_path, garbage=4, deflate=True)
        finally:
            doc.close()

        processor.validate_output_pdf(output_path, min_size=500)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except ValueError as exc:
        logger.warning("add_text_pdf: bad input — %s", exc, extra=context)
        raise ConversionError(str(exc), context=context) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in add_text_pdf",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(exc).__name__,
            },
        )
        raise ConversionError(
            "Unexpected error: %s" % exc,
            context={**context, "error_type": type(exc).__name__},
        ) from exc
