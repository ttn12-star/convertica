import os
import re
import shutil
import time
from collections.abc import Callable
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

from ...cooperative_stop import check as check_stop
from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)


def _flate_image_is_safe(doc: fitz.Document, xref: int) -> bool:
    """Whether a Flate image survives becoming an 8-bit Gray/RGB JPEG intact.

    Each skipped key breaks a naive re-encode: /Decode inverts the image once
    the pixmap has already applied it, a colour-key /Mask stops matching after
    JPEG noise, ImageMask/1-bit/Indexed art turns into blurry, larger JPEG,
    and CMYK is kept for print, as the JPEG branch does.
    """

    def key(name: str) -> str:
        try:
            return doc.xref_get_key(xref, name)[1] or "null"
        except Exception:
            return "null"

    if key("ImageMask") == "true" or key("BitsPerComponent") != "8":
        return False
    if key("Mask") != "null" or key("Decode") != "null":
        return False
    colorspace = key("ColorSpace")
    if colorspace in ("/DeviceGray", "/DeviceRGB"):
        return True
    # Scanner/phone output is often [/ICCBased <ref>], inline or by reference;
    # the caller still requires a 1- or 3-channel pixmap (Gray/RGB profile).
    if colorspace.endswith(" R"):
        try:
            colorspace = doc.xref_object(int(colorspace.split()[0]), compressed=True)
        except Exception:
            return False
    # The family is the first array element: [/Separation /Spot [/ICCBased ..] f]
    # and [/Indexed [/ICCBased ..] ..] also *contain* /ICCBased, but a 1-channel
    # tint is not gray (it rendered inverted) and a palette is not RGB.
    return colorspace.lstrip("[ ").startswith("/ICCBased")


def _icc_colorspace(doc: fitz.Document, xref: int) -> str | None:
    """The image's ColorSpace value if it is ICCBased, else None."""
    try:
        value = doc.xref_get_key(xref, "ColorSpace")[1] or ""
        resolved = (
            doc.xref_object(int(value.split()[0]), compressed=True)
            if value.endswith(" R")
            else value
        )
    except Exception:
        return None
    return value if resolved.lstrip("[ ").startswith("/ICCBased") else None


def _is_pdfa1(doc: fitz.Document) -> bool:
    """PDF/A-1 forbids object streams (PDF 1.4 base)."""
    try:
        xmp = doc.get_xml_metadata() or ""
    except Exception:
        return False
    return bool(re.search(r"pdfaid:part\W{1,3}1\b", xmp))


# (JPEG quality, longest image side in px), mildest first. The last step is
# roughly 65 dpi on an A4 scan: still readable, the floor for "make it fit".
TARGET_STEPS = [
    (70, 2400),
    (60, 1800),
    (50, 1400),
    (42, 1100),
    (35, 900),
    (28, 700),
    (22, 550),
]


# Extra seconds the target search may add on top of the plain compression.
# The page posts synchronously and Cloudflare cuts a request at 100 s.
TARGET_TIME_BUDGET = 45


def _shrink_to_target(
    processor, op, output_path: str, target: int, level: str, pass_seconds: float
) -> None:
    """Replace output_path with the mildest step result that fits target.

    Sizes fall as steps get harsher, so: try the harshest first (if even that
    doesn't fit, nothing will; keep the smallest file we have), binary search
    the rest, then one pass halfway between the step that missed and the one
    that fit, because the steps are coarse. At most ~5 extra passes, fewer
    when a pass is slow: the search stops at the best fit found so far once
    the next pass (estimated from the plain one) would overrun the budget.
    ponytail: per-pass estimate is linear; route big scans to async if needed.
    """
    tmp_dir = os.path.dirname(output_path)
    results = {}
    deadline = time.monotonic() + TARGET_TIME_BUDGET
    est = max(pass_seconds, 0.1) * 1.5  # image passes cost more than a plain save

    def affordable() -> bool:
        return time.monotonic() + est <= deadline

    def attempt(step: tuple[int, int]) -> int:
        path = os.path.join(tmp_dir, f"_target_q{step[0]}_d{step[1]}.pdf")
        processor.run_pdf_operation_with_repair(
            op, output_path=path, compression_level=level, step=step
        )
        results[step] = (os.path.getsize(path), path)
        return results[step][0]

    steps = TARGET_STEPS
    last = len(steps) - 1
    if not affordable():
        return  # keep the level's result; the page reports the miss
    if attempt(steps[last]) > target:
        best = steps[last]
        if results[best][0] >= os.path.getsize(output_path):
            best = None  # the level's own result is already the smallest
    else:
        lo, hi = 0, last  # invariant: steps[hi] fits
        while lo < hi and affordable():
            mid = (lo + hi) // 2
            if attempt(steps[mid]) <= target:
                hi = mid
            else:
                lo = mid + 1
        best = steps[hi]
        if hi > 0:
            (q1, d1), (q2, d2) = steps[hi - 1], steps[hi]
            between = ((q1 + q2) // 2, (d1 + d2) // 2)
            if between not in results and affordable() and attempt(between) <= target:
                best = between
    try:
        if best is not None:
            shutil.move(results[best][1], output_path)
    finally:
        for _, path in results.values():
            if os.path.exists(path):
                os.remove(path)


def compress_pdf(
    uploaded_file: UploadedFile,
    compression_level: str = "medium",
    suffix: str = "_convertica",
    check_cancelled: Callable[[], None] | None = None,
    target_size_kb: int | None = None,
    **kwargs,
) -> tuple[str, str]:
    """Compress PDF to reduce file size.

    Args:
        uploaded_file: PDF file to compress
        compression_level: Compression level ("low", "medium", "high")
        suffix: Suffix for output filename
        target_size_kb: When set and the level's result is bigger, lower image
            quality/resolution step by step and keep the mildest step that
            fits. If even the last step doesn't fit, the smallest result wins.

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
                    "use_objstms": 1,
                }
            if level == "medium":
                return {
                    "garbage": 2,
                    "deflate": True,
                    "clean": True,
                    "linear": False,
                    "deflate_images": True,
                    "deflate_fonts": True,
                    "use_objstms": 1,
                }
            return {
                "garbage": 3,
                "deflate": True,
                "clean": False,
                "linear": False,
                "deflate_images": False,
                "deflate_fonts": False,
                "use_objstms": 1,
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
                "use_objstms",
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

        def _recompress_jpegs(
            doc: fitz.Document, level: str, step: tuple[int, int] | None = None
        ) -> None:
            """step=(jpeg quality, max side px) overrides the level: target mode,
            where any saving counts and downscaling isn't capped at 75%."""
            if step is None and level not in {"medium", "high"}:
                return

            quality, max_dim = step or (_jpeg_quality(level), _jpeg_max_dim(level))
            seen = set()

            for page in doc:
                # Check cancellation at the start of each page
                if callable(check_cancelled):
                    check_cancelled()
                check_stop()  # abandoned by its task (time limit, cancel)
                for img in page.get_images(full=True):
                    xref = img[0]
                    if xref in seen:
                        continue
                    seen.add(xref)

                    # Filter first: extract_image re-encodes a Flate image to
                    # PNG (~1.5 s per scanned page) only for us to skip it.
                    try:
                        flt = doc.xref_get_key(xref, "Filter")[1] or ""
                    except Exception:
                        flt = ""

                    if flt == "/DCTDecode":
                        try:
                            img_bytes = doc.extract_image(xref).get("image")
                            im = Image.open(BytesIO(img_bytes))
                            im.load()
                        except Exception as e:
                            logger.debug(
                                "compress_pdf: skip image xref=%d — JPEG open failed: %s",
                                xref,
                                e,
                            )
                            continue
                        stored_size = len(img_bytes or b"")
                    elif flt == "/FlateDecode" and _flate_image_is_safe(doc, xref):
                        # Scans and PNGs: these were never touched, so a scanned
                        # PDF came out 0% smaller on every level.
                        try:
                            pix = fitz.Pixmap(doc, xref)
                            if pix.alpha or pix.n not in (1, 3):
                                continue
                            im = Image.frombytes(
                                "L" if pix.n == 1 else "RGB",
                                (pix.width, pix.height),
                                pix.samples,
                            )
                            del pix
                            stored_size = len(doc.xref_stream_raw(xref))
                        except Exception as e:
                            logger.debug(
                                "compress_pdf: skip image xref=%d — pixmap failed: %s",
                                xref,
                                e,
                            )
                            continue
                    else:
                        continue
                    icc = _icc_colorspace(doc, xref)
                    channels = len(im.getbands())
                    # A Flate original is lossless: JPEG has to earn its
                    # artifacts (screenshots with small text saved ~14%).
                    min_saving = 0.6 if flt == "/FlateDecode" else 0.9
                    if step:
                        min_saving = 1.0

                    # Skip images that are not RGB or grayscale to prevent color space issues
                    if im.mode not in {"RGB", "L", "CMYK"}:
                        try:
                            im = im.convert("RGB")
                        except Exception as e:
                            logger.debug(
                                "compress_pdf: skip image xref=%d mode=%s — convert to RGB failed: %s",
                                xref,
                                im.mode,
                                e,
                            )
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
                            not step and new_pixels < original_pixels * 0.25
                        ):  # Don't reduce by more than 75%
                            continue

                        try:
                            im = im.resize(new_size, Image.LANCZOS)
                        except Exception:
                            pass

                    out = BytesIO()
                    try:
                        im.save(out, format="JPEG", quality=quality, optimize=True)
                    except Exception as e:
                        logger.debug(
                            "compress_pdf: skip image xref=%d — JPEG re-save failed: %s",
                            xref,
                            e,
                        )
                        continue

                    new_bytes = out.getvalue()
                    if not new_bytes:
                        continue

                    # Only replace if we save at least 10% (not just any reduction)
                    if len(new_bytes) >= stored_size * min_saving:
                        continue

                    try:
                        # compress=False: the default would deflate a JPEG that
                        # happens to shrink and set /FlateDecode, which the
                        # /DCTDecode below would then contradict.
                        doc.update_stream(xref, new_bytes, compress=False)
                        # update_stream swaps bytes only; a resized image
                        # needs its declared dimensions updated too or
                        # viewers render garbage.
                        doc.xref_set_key(xref, "Width", str(im.width))
                        doc.xref_set_key(xref, "Height", str(im.height))
                        doc.xref_set_key(xref, "Filter", "/DCTDecode")
                        doc.xref_set_key(xref, "DecodeParms", "null")
                        # Samples are still in the image's ICC space: keep the
                        # profile, or Adobe RGB/ProPhoto shifted colour as sRGB.
                        if not (icc and len(im.getbands()) == channels):
                            doc.xref_set_key(
                                xref,
                                "ColorSpace",
                                "/DeviceGray" if im.mode == "L" else "/DeviceRGB",
                            )
                        doc.xref_set_key(xref, "BitsPerComponent", "8")
                    except Exception as e:
                        logger.debug(
                            "compress_pdf: skip image xref=%d — update_stream failed: %s",
                            xref,
                            e,
                        )
                        continue

        def _op(
            input_pdf_path: str,
            *,
            output_path: str,
            compression_level: str,
            step: tuple[int, int] | None = None,
        ):
            # Check cancellation before opening document
            if callable(check_cancelled):
                check_cancelled()

            doc = fitz.open(input_pdf_path)
            try:
                if compression_level == "high" and step is None:
                    for page in doc:
                        # Check cancellation for each page
                        if callable(check_cancelled):
                            check_cancelled()
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

                _recompress_jpegs(doc, compression_level, step)
                kwargs = _save_kwargs("high" if step else compression_level)
                if _is_pdfa1(doc):
                    kwargs.pop("use_objstms", None)
                _save_with_fallback(doc, output_path, kwargs)
            finally:
                doc.close()

            try:
                in_size = os.path.getsize(input_pdf_path)
                out_size = os.path.getsize(output_path)
                if in_size > 0 and out_size > in_size and compression_level != "low":
                    doc2 = fitz.open(input_pdf_path)
                    try:
                        kwargs = _save_kwargs("low")
                        if _is_pdfa1(doc2):
                            kwargs.pop("use_objstms", None)
                        _save_with_fallback(doc2, output_path, kwargs)
                    finally:
                        doc2.close()
                # Last resort: an already-optimized PDF can still grow on
                # re-save even at "low". Never hand back a file bigger than the
                # input — copy the original so "compress" never inflates.
                if in_size > 0 and os.path.getsize(output_path) >= in_size:
                    shutil.copyfile(input_pdf_path, output_path)
            except Exception:
                pass

            return output_path

        started = time.monotonic()
        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            compression_level=compression_level,
        )
        target = target_size_kb * 1024 if target_size_kb else None
        if target and os.path.getsize(output_path) > target:
            _shrink_to_target(
                processor,
                _op,
                output_path,
                target,
                compression_level,
                pass_seconds=time.monotonic() - started,
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
