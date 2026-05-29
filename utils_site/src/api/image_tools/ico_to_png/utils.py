"""Convert a .ico file to PNG, extracting the largest embedded frame."""

import os
import tempfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger

logger = get_logger(__name__)


def ico_to_png(ico_file) -> tuple[str, str]:
    """Extract the largest frame from a .ico and save it as PNG.

    Returns (input_file_path, output_file_path).
    """
    tmp_dir = tempfile.mkdtemp(prefix="ico2png_")
    safe_name = sanitize_filename(os.path.basename(ico_file.name or "favicon.ico"))
    input_path = os.path.join(tmp_dir, safe_name)
    with open(input_path, "wb") as f:
        for chunk in ico_file.chunks():
            f.write(chunk)

    base_name = os.path.splitext(safe_name)[0]
    output_path = os.path.join(tmp_dir, f"{base_name}.png")

    with Image.open(input_path) as img:
        # Pillow's ICO plugin exposes all embedded sizes; pick the largest.
        try:
            largest = max(img.ico.sizes(), key=lambda s: s[0] * s[1])
            frame = img.ico.getimage(largest)
        except AttributeError:
            frame = img  # not an IcoImageFile; use as-is
        out_img = frame.convert("RGBA")
        out_img.save(output_path, "PNG", optimize=True)

    logger.info(
        "ICO converted to PNG",
        extra={"input_path": input_path, "output_path": output_path},
    )
    return input_path, output_path
