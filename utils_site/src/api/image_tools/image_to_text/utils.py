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


def _write_txt(text: str, path: str) -> None:
    """Write the extracted text to a UTF-8 .txt file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_docx(text: str, path: str) -> None:
    """Write the extracted text to a .docx file, one paragraph per line.

    Empty lines become empty paragraphs so blank-line/paragraph structure from
    the OCR reconstruction is preserved. Premium feature.
    """
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def run_image_ocr(
    image_file,
    language: str = "auto",
    confidence_threshold: int = 60,
    output_format: str = "txt",
) -> tuple[str, str]:
    """Extract text from an uploaded image and write it to a .txt or .docx file.

    Returns (input_path, output_path) so it slots into BaseConversionAPIView's
    standard streaming-response flow. ``output_format`` is "txt" (default,
    text/plain) or "docx" (premium Word export).
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

    try:
        text = extract_text_from_image(
            rgb,
            user_language=language,
            confidence_threshold=confidence_threshold,
        )
    finally:
        rgb.close()  # release the converted-image buffer (mirrors convert_heic)

    base_name = os.path.splitext(safe_name)[0]
    fmt = (output_format or "txt").lower()
    if fmt == "docx":
        output_path = os.path.join(tmp_dir, f"{base_name}.docx")
        _write_docx(text, output_path)
    else:
        output_path = os.path.join(tmp_dir, f"{base_name}.txt")
        _write_txt(text, output_path)

    logger.info(
        "Image OCR completed",
        extra={
            "input_path": input_path,
            "output_path": output_path,
            "language": language,
            "output_format": fmt,
            "text_length": len(text),
        },
    )
    return input_path, output_path
