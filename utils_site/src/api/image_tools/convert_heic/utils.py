"""HEIC / HEIF image conversion utility.

Decodes Apple HEIC / HEIF photos via the pillow-heif plugin and re-encodes
them to JPEG, PNG, or single-page PDF using Pillow.
"""

import os
import tempfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger

logger = get_logger(__name__)

# Register pillow-heif as a Pillow plugin on first import of this module.
# The registration is idempotent — pillow-heif guards against double-registration —
# so it's safe under Django's reload-on-change dev server too.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:  # pragma: no cover — covered by requirements.txt pin
    _HEIF_AVAILABLE = False
    logger.warning("pillow-heif is not installed; HEIC converter will fail with a 500.")


# Output format → extension
EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "PDF": ".pdf",
}

# Pillow save format names
PILLOW_FORMAT = {
    "JPEG": "JPEG",
    "PNG": "PNG",
    "PDF": "PDF",
}


def _normalise_output_format(output_format: str) -> str:
    """Return a canonical output format key or raise ValueError."""
    fmt = (output_format or "").upper()
    if fmt in ("JPG", "JPEG"):
        return "JPEG"
    if fmt == "PNG":
        return "PNG"
    if fmt == "PDF":
        return "PDF"
    raise ValueError(f"Unsupported output format: {output_format!r}")


def convert_heic(
    image_file,
    output_format: str = "JPEG",
    quality: int = 90,
) -> tuple[str, str]:
    """Convert a HEIC / HEIF image to JPEG, PNG, or PDF.

    Args:
        image_file: Uploaded HEIC/HEIF file (Django UploadedFile or file-like).
        output_format: One of 'JPEG' ('JPG' alias accepted), 'PNG', 'PDF'.
        quality: Quality for lossy formats (10–100, default 90). Ignored for PNG.

    Returns:
        (input_file_path, output_file_path)
    """
    fmt = _normalise_output_format(output_format)

    tmp_dir = tempfile.mkdtemp(prefix="convert_heic_")

    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.heic"))
    input_path = os.path.join(tmp_dir, safe_name)

    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    base_name = os.path.splitext(safe_name)[0]
    out_ext = EXTENSIONS[fmt]
    output_filename = f"{base_name}_convertica{out_ext}"
    output_path = os.path.join(tmp_dir, output_filename)

    with Image.open(input_path) as img:
        img_copy = img.copy()

    _save_converted(img_copy, output_path, fmt, quality)
    img_copy.close()

    logger.info(
        "HEIC converted",
        extra={
            "input_path": input_path,
            "output_path": output_path,
            "output_format": fmt,
            "quality": quality,
        },
    )

    return input_path, output_path


def _save_converted(img: Image.Image, output_path: str, fmt: str, quality: int) -> None:
    """Save image in the target format, normalising mode where required."""
    pillow_fmt = PILLOW_FORMAT[fmt]

    if fmt == "JPEG":
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, pillow_fmt, quality=quality, optimize=True)

    elif fmt == "PNG":
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(output_path, pillow_fmt, optimize=True)

    elif fmt == "PDF":
        # PDF backend doesn't support RGBA — flatten alpha to white background.
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, pillow_fmt, resolution=144.0)
