"""Image to Text (OCR) utility: decode an image and extract plain text."""

import os
import tempfile

from PIL import Image

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger
from ...ocr_utils import extract_text_from_image

logger = get_logger(__name__)

# Register pillow-heif so PIL can decode Apple HEIC/HEIF. Idempotent — safe under
# the dev server's reload — mirrors convert_heic/utils.py.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover — pinned in requirements.txt
    logger.warning("pillow-heif not installed; HEIC input to OCR will fail with 500.")


def run_image_ocr(
    image_file,
    language: str = "auto",
    confidence_threshold: int = 60,
) -> tuple[str, str]:
    """Extract text from an uploaded image and write it to a .txt file.

    Returns (input_path, output_path) so it slots into BaseConversionAPIView's
    standard streaming-response flow; the output is a UTF-8 text/plain file.
    """
    tmp_dir = tempfile.mkdtemp(prefix="image_to_text_")
    safe_name = sanitize_filename(os.path.basename(image_file.name or "image.png"))
    input_path = os.path.join(tmp_dir, safe_name)

    with open(input_path, "wb") as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    with Image.open(input_path) as img:
        # First frame to RGB (covers animated GIF / multi-page TIFF / palette / CMYK).
        rgb = img.convert("RGB")

    text = extract_text_from_image(
        rgb,
        user_language=language,
        confidence_threshold=confidence_threshold,
    )

    base_name = os.path.splitext(safe_name)[0]
    output_path = os.path.join(tmp_dir, f"{base_name}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info(
        "Image OCR completed",
        extra={
            "input_path": input_path,
            "output_path": output_path,
            "language": language,
            "text_length": len(text),
        },
    )
    return input_path, output_path
