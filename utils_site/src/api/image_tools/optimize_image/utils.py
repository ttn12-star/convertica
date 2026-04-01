"""
Image optimization utility for reduce file size while maintaining quality.
"""

import io
import os
import tempfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger

logger = get_logger(__name__)

# Map format names to file extensions
FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WebP": ".webp",
    "GIF": ".gif",
}


def optimize_image(
    image_file,
    quality: int = 85,
    output_format: str = None,
    max_width: int = None,
    max_height: int = None,
) -> tuple[str, str]:
    """
    Optimize an image by compressing it and optionally resizing it.

    Args:
        image_file: Uploaded image file (Django UploadedFile or file-like object)
        quality: Compression quality (10-100, default 85)
        output_format: Output format string ('JPEG', 'PNG', 'WebP') or None to keep original
        max_width: Maximum width in pixels (optional, maintains aspect ratio)
        max_height: Maximum height in pixels (optional, maintains aspect ratio)

    Returns:
        Tuple[str, str]: (input_file_path, output_file_path)
    """
    tmp_dir = tempfile.mkdtemp(prefix="optimize_img_")

    # Save uploaded file to temp
    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.jpg"))
    input_path = os.path.join(tmp_dir, safe_name)

    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    # Open with Pillow
    with Image.open(input_path) as img:
        # Detect original format
        original_format = img.format or "JPEG"

        # Determine output format
        if output_format and output_format.upper() in FORMAT_EXTENSIONS:
            out_format = output_format.upper()
        else:
            # Keep original format; normalise format name for Pillow
            fmt_map = {
                "JPEG": "JPEG",
                "JPG": "JPEG",
                "PNG": "PNG",
                "WEBP": "WebP",
                "GIF": "GIF",
            }
            out_format = fmt_map.get(original_format.upper(), "JPEG")

        # Normalise "WebP" -> "WEBP" for extension lookup
        ext_key = out_format.upper() if out_format.upper() != "WEBP" else "WebP"
        out_ext = FORMAT_EXTENSIONS.get(
            ext_key, FORMAT_EXTENSIONS.get(out_format, ".jpg")
        )

        # Build output filename
        base_name = os.path.splitext(safe_name)[0]
        output_filename = f"{base_name}_optimized{out_ext}"
        output_path = os.path.join(tmp_dir, output_filename)

        # Resize if max dimensions supplied (thumbnail keeps aspect ratio)
        if max_width or max_height:
            target_width = max_width or img.width
            target_height = max_height or img.height
            img.thumbnail((target_width, target_height), Image.LANCZOS)

        # Copy image to allow further manipulation after context manager
        img_copy = img.copy()

    # Now save the (possibly resized) copy
    _save_optimized(img_copy, output_path, out_format, quality)
    img_copy.close()

    logger.info(
        "Image optimized",
        extra={
            "input_path": input_path,
            "output_path": output_path,
            "out_format": out_format,
            "quality": quality,
        },
    )

    return input_path, output_path


def _save_optimized(img: Image.Image, output_path: str, fmt: str, quality: int) -> None:
    """Save image with format-specific optimisation settings."""
    fmt_upper = fmt.upper()

    if fmt_upper == "JPEG":
        # JPEG does not support alpha channel
        if img.mode in ("RGBA", "LA", "P") or img.mode != "RGB":
            img = img.convert("RGB")
        img.save(
            output_path,
            "JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )

    elif fmt_upper == "PNG":
        img.save(
            output_path,
            "PNG",
            optimize=True,
            compress_level=9,
        )

    elif fmt_upper in ("WEBP", "WebP"):
        img.save(
            output_path,
            "WebP",
            quality=quality,
            method=6,
        )

    elif fmt_upper == "GIF":
        # GIF is palette-based
        if img.mode not in ("P", "L"):
            img = img.convert("P", palette=Image.ADAPTIVE)
        img.save(output_path, "GIF", optimize=True)

    else:
        # Fallback: save as-is
        img.save(output_path)
