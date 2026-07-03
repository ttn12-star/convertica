"""SVG rasterization helpers (svglib + reportlab renderPM).

Used by the svg-to-ico page and SVG input to the favicon generator. Renders an
SVG to a square PNG of `target_px`, scaling the drawing up so small source SVGs
still produce crisp large icons.
"""

import os
import re

from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from ..logging_utils import get_logger

logger = get_logger(__name__)

# <image> href / xlink:href values. svglib resolves a non-data href as a local
# filesystem path relative to the SVG, so an attacker-supplied SVG with an
# absolute or ../ href would rasterize an arbitrary local file into the output
# (LFI). We only ever want inline data: images, so anything else is rejected.
_IMAGE_HREF_RE = re.compile(
    rb"<image\b[^>]*?\b(?:xlink:)?href\s*=\s*([\"'])(.*?)\1",
    re.IGNORECASE | re.DOTALL,
)


def is_svg(path: str) -> bool:
    """Return True if the path looks like an SVG by extension."""
    return path.lower().endswith(".svg")


def _reject_external_image_refs(svg_bytes: bytes) -> None:
    """Raise ValueError if the SVG embeds an <image> with a non-data href.

    Blocks the local-file-read vector: only inline `data:` images are allowed.
    """
    for _quote, href in _IMAGE_HREF_RE.findall(svg_bytes):
        if not href.lstrip().lower().startswith(b"data:"):
            raise ValueError("SVG references an external image, which is not allowed")


def rasterize_svg_to_png(svg_path: str, out_dir: str, target_px: int = 512) -> str:
    """Rasterize an SVG file to a PNG `target_px` on its longest side.

    Returns the output PNG path (inside out_dir). Raises ValueError if the SVG
    cannot be parsed or references an external image (LFI guard).
    """
    with open(svg_path, "rb") as f:
        _reject_external_image_refs(f.read())

    drawing = svg2rlg(svg_path)
    if drawing is None or not drawing.width or not drawing.height:
        raise ValueError("Could not parse SVG or SVG has no intrinsic size")

    scale = target_px / max(drawing.width, drawing.height)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)

    out_path = os.path.join(out_dir, "rasterized.png")
    renderPM.drawToFile(drawing, out_path, fmt="PNG")
    logger.info("SVG rasterized", extra={"svg_path": svg_path, "target_px": target_px})
    return out_path
