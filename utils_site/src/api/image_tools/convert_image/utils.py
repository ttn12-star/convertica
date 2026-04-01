"""
Image format conversion utility.
Converts between JPEG, PNG, WebP, GIF, BMP, and TIFF formats using Pillow.
"""

import os
import tempfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger

logger = get_logger(__name__)

# Map output format name -> file extension
EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WebP": ".webp",
    "GIF": ".gif",
    "BMP": ".bmp",
    "TIFF": ".tiff",
}

# Pillow save format names (some differ from canonical display names)
PILLOW_FORMAT = {
    "JPEG": "JPEG",
    "PNG": "PNG",
    "WebP": "WebP",
    "GIF": "GIF",
    "BMP": "BMP",
    "TIFF": "TIFF",
}


def convert_image(
    image_file,
    output_format: str,
    quality: int = 90,
) -> tuple[str, str]:
    """
    Convert an image to the specified output format.

    Args:
        image_file: Uploaded image file (Django UploadedFile or file-like object)
        output_format: Target format string — one of 'JPEG', 'PNG', 'WebP', 'GIF', 'BMP', 'TIFF'
        quality: Quality for lossy formats (10-100, default 90)

    Returns:
        Tuple[str, str]: (input_file_path, output_file_path)
    """
    fmt = output_format.upper() if output_format else "JPEG"
    # Normalise "WEBP" -> "WebP" to match EXTENSIONS keys
    if fmt == "WEBP":
        fmt = "WebP"

    if fmt not in EXTENSIONS:
        raise ValueError(f"Unsupported output format: {output_format}")

    tmp_dir = tempfile.mkdtemp(prefix="convert_img_")

    # Save uploaded file to temp
    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.jpg"))
    input_path = os.path.join(tmp_dir, safe_name)

    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    # Build output path
    base_name = os.path.splitext(safe_name)[0]
    out_ext = EXTENSIONS[fmt]
    output_filename = f"{base_name}_converted{out_ext}"
    output_path = os.path.join(tmp_dir, output_filename)

    # Open and convert
    with Image.open(input_path) as img:
        img_copy = img.copy()

    _save_converted(img_copy, output_path, fmt, quality)
    img_copy.close()

    logger.info(
        "Image converted",
        extra={
            "input_path": input_path,
            "output_path": output_path,
            "output_format": fmt,
            "quality": quality,
        },
    )

    return input_path, output_path


def _save_converted(img: Image.Image, output_path: str, fmt: str, quality: int) -> None:
    """Save image in the target format with appropriate mode conversion."""
    pillow_fmt = PILLOW_FORMAT.get(fmt, fmt)

    if fmt == "JPEG":
        # JPEG does not support alpha channels or palette mode
        if img.mode in ("RGBA", "LA", "P") or img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, pillow_fmt, quality=quality, optimize=True)

    elif fmt == "PNG":
        # PNG supports RGBA — keep alpha if present
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA")
        img.save(output_path, pillow_fmt, optimize=True)

    elif fmt == "WebP":
        # WebP supports RGBA
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(output_path, pillow_fmt, quality=quality, method=6)

    elif fmt == "GIF":
        # GIF is 8-bit palette; quantise to 256 colours
        if img.mode not in ("P", "L"):
            img = img.convert("P", palette=Image.ADAPTIVE)
        img.save(output_path, pillow_fmt, optimize=True)

    elif fmt == "BMP":
        # BMP supports RGB and RGBA
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")
        img.save(output_path, pillow_fmt)

    elif fmt == "TIFF":
        # TIFF supports most modes — no special conversion needed
        img.save(output_path, pillow_fmt)

    else:
        img.save(output_path)
