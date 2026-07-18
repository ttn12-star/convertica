"""Convert a raster/SVG image to a multi-resolution Windows .ico favicon."""

import os
import tempfile

from PIL import Image, ImageOps
from src.exceptions import ConversionError

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger
from ..svg_raster import is_svg, rasterize_svg_to_png

logger = get_logger(__name__)

DEFAULT_SIZES = (16, 32, 48)
ALLOWED_SIZES = (16, 24, 32, 48, 64, 128, 256)


def image_to_ico(image_file, sizes=DEFAULT_SIZES) -> tuple[str, str]:
    """Convert an uploaded image to a multi-resolution .ico file.

    Args:
        image_file: Django UploadedFile (raster image or SVG).
        sizes: iterable of square pixel sizes to embed (default 16/32/48).

    Returns:
        (input_file_path, output_file_path)
    """
    sizes = tuple(s for s in sizes if s in ALLOWED_SIZES) or DEFAULT_SIZES

    tmp_dir = tempfile.mkdtemp(prefix="img2ico_")
    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.png"))
    input_path = os.path.join(tmp_dir, safe_name)
    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    raster_path = input_path
    if is_svg(input_path):
        try:
            raster_path = rasterize_svg_to_png(
                input_path, tmp_dir, target_px=max(sizes)
            )
        except ValueError as exc:
            # Unparseable SVG or a disallowed external <image> ref is bad user
            # input, not a server fault → 400 instead of 500.
            raise ConversionError(str(exc)) from exc

    with Image.open(raster_path) as img:
        src = img.convert("RGBA")

    # Favicons are square. Center-crop/scale the source to a square canvas at the
    # largest requested size so Pillow can emit every requested frame as a proper
    # square (it will not upscale a smaller source, nor keep non-square frames).
    max_px = max(sizes)
    src = ImageOps.fit(src, (max_px, max_px))

    base_name = os.path.splitext(safe_name)[0]
    output_path = os.path.join(tmp_dir, f"{base_name}.ico")
    src.save(output_path, format="ICO", sizes=[(s, s) for s in sorted(sizes)])
    src.close()

    logger.info(
        "Image converted to ICO",
        extra={"input_path": input_path, "output_path": output_path, "sizes": sizes},
    )
    return input_path, output_path
