"""Generate a complete favicon package (ZIP) from one source image."""

import json
import os
import tempfile
import zipfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger
from ..svg_raster import is_svg, rasterize_svg_to_png

logger = get_logger(__name__)

ICO_SIZES = (16, 32, 48)
PNG_ICONS = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "favicon-48x48.png": 48,
    "apple-touch-icon.png": 180,
    "android-chrome-192x192.png": 192,
    "android-chrome-512x512.png": 512,
}

MANIFEST = {
    "name": "",
    "short_name": "",
    "icons": [
        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
    ],
    "theme_color": "#ffffff",
    "background_color": "#ffffff",
    "display": "standalone",
}

SNIPPET = (
    '<link rel="icon" type="image/x-icon" href="/favicon.ico">\n'
    '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">\n'
    '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">\n'
    '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">\n'
    '<link rel="manifest" href="/site.webmanifest">\n'
    '<meta name="theme-color" content="#ffffff">\n'
)


def generate_favicon(image_file) -> tuple[str, str]:
    """Build a favicon package ZIP from a source image.

    Returns (input_file_path, output_zip_path).
    """
    tmp_dir = tempfile.mkdtemp(prefix="favicon_")
    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.png"))
    input_path = os.path.join(tmp_dir, safe_name)
    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    raster_path = input_path
    if is_svg(input_path):
        raster_path = rasterize_svg_to_png(input_path, tmp_dir, target_px=512)

    with Image.open(raster_path) as img:
        src = img.convert("RGBA")

    assets_dir = os.path.join(tmp_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    ico_path = os.path.join(assets_dir, "favicon.ico")
    src.save(ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES])

    for filename, px in PNG_ICONS.items():
        resized = src.resize((px, px), Image.LANCZOS)
        resized.save(os.path.join(assets_dir, filename), "PNG", optimize=True)
        resized.close()

    with open(os.path.join(assets_dir, "site.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, indent=2)

    with open(os.path.join(assets_dir, "snippet.html"), "w", encoding="utf-8") as f:
        f.write(SNIPPET)

    src.close()

    base_name = os.path.splitext(safe_name)[0]
    output_path = os.path.join(tmp_dir, f"{base_name}_favicon.zip")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in os.listdir(assets_dir):
            zf.write(os.path.join(assets_dir, member), arcname=member)

    logger.info(
        "Favicon package generated",
        extra={"input_path": input_path, "output_path": output_path},
    )
    return input_path, output_path
