import os
from io import BytesIO

import fitz
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)


def compress_pdf(
    uploaded_file: UploadedFile,
    compression_level: str = "medium",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Compress PDF to reduce file size.

    Args:
        uploaded_file: PDF file to compress
        compression_level: Compression level ("low", "medium", "high")
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "compress_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "compression_level": compression_level,
    }

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="compress_pdf_",
            required_mb=300,
            context=context,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = f"{base}_compressed{suffix}.pdf"
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _save_kwargs(level: str) -> dict:
            if level == "high":
                return {
                    "garbage": 4,
                    "deflate": True,
                    "clean": True,
                    "linear": False,
                    "deflate_images": True,
                    "deflate_fonts": True,
                    "compression_effort": 9,
                }
            if level == "medium":
                return {
                    "garbage": 2,
                    "deflate": True,
                    "clean": True,
                    "linear": False,
                    "deflate_images": True,
                    "deflate_fonts": True,
                    "compression_effort": 6,
                }
            return {
                "garbage": 1,
                "deflate": True,
                "clean": False,
                "linear": False,
                "deflate_images": False,
                "deflate_fonts": False,
                "compression_effort": 2,
            }

        def _save_with_fallback(
            doc: fitz.Document, output_path: str, save_kwargs: dict
        ) -> None:
            """Save with best-effort compatibility across PyMuPDF versions."""

            try:
                doc.save(output_path, **save_kwargs)
                return
            except TypeError:
                pass

            # Older PyMuPDF versions may not support these kwargs.
            reduced = dict(save_kwargs)
            for key in [
                "deflate_images",
                "deflate_fonts",
                "compression_effort",
                "linear",
            ]:
                reduced.pop(key, None)
            doc.save(output_path, **reduced)

        def _jpeg_quality(level: str) -> int:
            # Increased quality to prevent black pages with noise
            if level == "high":
                return 65  # Was 40 - too aggressive, caused artifacts
            if level == "medium":
                return 75  # Was 60 - increased for better quality
            return 85  # Was 80

        def _jpeg_max_dim(level: str) -> int:
            # Increased dimensions to preserve quality
            if level == "high":
                return 2000  # Was 1600 - too small, caused quality loss
            if level == "medium":
                return 2800  # Was 2400
            return 4000

        def _recompress_jpegs(doc: fitz.Document, level: str) -> None:
            if level not in {"medium", "high"}:
                return

            quality = _jpeg_quality(level)
            max_dim = _jpeg_max_dim(level)
            seen = set()

            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    if xref in seen:
                        continue
                    seen.add(xref)

                    try:
                        info = doc.extract_image(xref)
                    except Exception:
                        continue

                    ext = (info.get("ext") or "").lower()
                    if ext not in {"jpeg", "jpg"}:
                        continue

                    try:
                        flt = doc.xref_get_key(xref, "Filter")[1]
                    except Exception:
                        flt = ""
                    if "DCTDecode" not in (flt or ""):
                        continue

                    img_bytes = info.get("image")
                    if not img_bytes:
                        continue

                    try:
                        im = Image.open(BytesIO(img_bytes))
                        im.load()
                    except Exception:
                        continue

                    # Skip images that are not RGB or grayscale to prevent color space issues
                    if im.mode not in {"RGB", "L", "CMYK"}:
                        try:
                            im = im.convert("RGB")
                        except Exception:
                            continue

                    # Preserve CMYK images for print quality
                    if im.mode == "CMYK":
                        continue

                    w, h = im.size
                    original_pixels = w * h

                    # Skip very small images - compression won't help much
                    if original_pixels < 10000:  # Less than 100x100
                        continue

                    max_side = max(w, h)
                    if max_side > max_dim:
                        scale = max_dim / float(max_side)
                        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))

                        # Don't resize if it would reduce quality too much
                        new_pixels = new_size[0] * new_size[1]
                        if (
                            new_pixels < original_pixels * 0.25
                        ):  # Don't reduce by more than 75%
                            continue

                        try:
                            im = im.resize(new_size, Image.LANCZOS)
                        except Exception:
                            pass

                    out = BytesIO()
                    try:
                        im.save(out, format="JPEG", quality=quality, optimize=True)
                    except Exception:
                        continue

                    new_bytes = out.getvalue()
                    if not new_bytes:
                        continue

                    # Only replace if we save at least 10% (not just any reduction)
                    if len(new_bytes) >= len(img_bytes) * 0.9:
                        continue

                    try:
                        doc.update_stream(xref, new_bytes)
                    except Exception:
                        continue

        def _op(input_pdf_path: str, *, output_path: str, compression_level: str):
            doc = fitz.open(input_pdf_path)
            try:
                if compression_level == "high":
                    for page in doc:
                        try:
                            page.set_links([])
                        except Exception:
                            pass
                        try:
                            annot = page.first_annot
                            while annot:
                                nxt = annot.next
                                page.delete_annot(annot)
                                annot = nxt
                        except Exception:
                            pass

                _recompress_jpegs(doc, compression_level)
                _save_with_fallback(doc, output_path, _save_kwargs(compression_level))
            finally:
                doc.close()

            try:
                in_size = os.path.getsize(input_pdf_path)
                out_size = os.path.getsize(output_path)
                if in_size > 0 and out_size > in_size and compression_level != "low":
                    doc2 = fitz.open(input_pdf_path)
                    try:
                        _save_with_fallback(doc2, output_path, _save_kwargs("low"))
                    finally:
                        doc2.close()
            except Exception:
                pass

            return output_path

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            compression_level=compression_level,
        )
        processor.validate_output_pdf(output_path, min_size=1000)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
