"""Convert a PDF to archival PDF/A (ISO 19005) using Ghostscript.

Ghostscript embeds fonts, flattens transparency (for PDF/A-1b), and converts
colours to an ICC OutputIntent — the things a conformant archival PDF requires.
After conversion we run a lightweight structural check with pikepdf (the output
must actually carry an /OutputIntents entry and an XMP ``pdfaid:part`` matching
the requested level). This is NOT a full veraPDF validation (no JVM in the
container); it only guarantees we never hand back a file that plainly is not
PDF/A. See the tool FAQ for the honest caveat.
"""

import glob
import os
import re
import subprocess

import fitz
from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)

# conformance choice -> (gs -dPDFA level, expected XMP pdfaid:part)
_LEVELS = {"pdfa-1b": ("1", "1"), "pdfa-2b": ("2", "2"), "pdfa-3b": ("3", "3")}
_DEF_TEMPLATE = os.path.join(os.path.dirname(__file__), "pdfa_def.ps.template")
# Big scans through gs are slow; the async/batch path handles the truly huge ones.
_GS_TIMEOUT = 300


def _resolve_icc() -> str:
    """Return the path to an RGB ICC profile bundled with the installed
    Ghostscript. The directory is version-specific (host gs 9.55 ships
    ``srgb.icc``/``default_rgb.icc``; the container gs 10.x differs) so we glob
    at runtime rather than hardcode a path that would break across images."""
    for name in ("srgb.icc", "default_rgb.icc", "esrgb.icc"):
        hits = glob.glob(f"/usr/share/ghostscript/*/iccprofiles/{name}")
        if hits:
            return sorted(hits)[-1]  # newest ghostscript directory
    raise ConversionError("No RGB ICC profile found in the Ghostscript installation")


def _render_def_ps(tmp_dir: str, icc_path: str, title: str) -> str:
    """Write the per-request PDFA_def.ps with the real ICC path and title."""
    with open(_DEF_TEMPLATE, encoding="utf-8") as fh:
        body = fh.read()
    # PostScript string literals treat ( ) \ specially; the ICC path has none,
    # but the user-supplied title might, so strip them.
    safe_title = title.replace("\\", "").replace("(", "").replace(")", "")[:120]
    body = body.replace("__ICC_PATH__", icc_path).replace("__TITLE__", safe_title)
    out = os.path.join(tmp_dir, "pdfa_def.ps")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    return out


def _verify_pdfa(path: str, expected_part: str, context: dict) -> None:
    """Fail loudly unless the output declares PDF/A conformance: an
    OutputIntents entry in the catalog plus an XMP ``pdfaid:part`` equal to the
    requested level. Structural only (via PyMuPDF) — not a full ISO 19005
    validation; the FAQ says so honestly."""
    doc = None
    try:
        doc = fitz.open(path)
        oi_type, oi_value = doc.xref_get_key(doc.pdf_catalog(), "OutputIntents")
        if oi_type == "null" or not oi_value:
            raise ConversionError(
                "Ghostscript produced a file without a PDF/A OutputIntent.",
                context=context,
            )
        xmp = doc.get_xml_metadata() or ""
        match = re.search(r"pdfaid:part[^0-9]{0,8}(\d+)", xmp)
        part = match.group(1) if match else ""
        if part != expected_part:
            raise ConversionError(
                "Output declares PDF/A part %r, expected %r." % (part, expected_part),
                context=context,
            )
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(
            "Could not verify PDF/A conformance of the output: %s" % e,
            context=context,
        ) from e
    finally:
        if doc is not None:
            doc.close()


def convert_pdf_to_pdfa(
    uploaded_file: UploadedFile,
    conformance: str = "pdfa-2b",
    suffix: str = "_convertica",
    **kwargs,
) -> tuple[str, str]:
    """Convert ``uploaded_file`` to PDF/A and verify the result.

    Args:
        uploaded_file: source PDF.
        conformance: ``pdfa-1b`` | ``pdfa-2b`` (default) | ``pdfa-3b``.
        suffix: appended to the output filename.

    Returns:
        (input_path, output_path).

    Raises:
        EncryptedPDFError: input is password-protected.
        ConversionError: gs failed, timed out, or the output is not conformant.
    """
    context = {
        "function": "convert_pdf_to_pdfa",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "conformance": conformance,
    }
    level, expected_part = _LEVELS.get(conformance, _LEVELS["pdfa-2b"])

    try:
        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="pdf_to_pdfa_",
            required_mb=400,
            context=context,
        )
        pdf_path = processor.prepare()

        # Encrypted input cannot be re-rendered by gs — reject early (protect_pdf pattern).
        try:
            if PdfReader(pdf_path).is_encrypted:
                raise EncryptedPDFError(
                    "This PDF is password-protected. Please unlock it first, "
                    "then convert it to PDF/A.",
                    context=context,
                )
        except EncryptedPDFError:
            raise
        except Exception:
            pass

        icc_path = _resolve_icc()
        def_ps = _render_def_ps(processor.tmp_dir, icc_path, title=uploaded_file.name)

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(processor.tmp_dir, "%s_pdfa%s.pdf" % (base, suffix))
        context["output_path"] = output_path

        # SAFER stays on (input is untrusted); --permit-file-read opens exactly the
        # one ICC file the prelude reads, nothing else.
        cmd = [
            "gs",
            "-dPDFA=%s" % level,
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-dPDFACompatibilityPolicy=1",
            "-sColorConversionStrategy=UseDeviceIndependentColor",
            "-sDEVICE=pdfwrite",
            "--permit-file-read=%s" % icc_path,
            "-sOutputFile=%s" % output_path,
            def_ps,
            pdf_path,
        ]
        try:
            result = subprocess.run(
                cmd, timeout=_GS_TIMEOUT, capture_output=True, text=True, check=True
            )
            logger.info(
                "Ghostscript PDF/A conversion complete",
                extra={
                    **context,
                    "event": "gs_complete",
                    "stdout": (result.stdout or "")[:500],
                },
            )
        except subprocess.TimeoutExpired as e:
            raise ConversionError(
                "PDF/A conversion timed out. Try a smaller document.",
                context=context,
            ) from e
        except subprocess.CalledProcessError as e:
            logger.error(
                "Ghostscript failed",
                extra={
                    **context,
                    "event": "gs_error",
                    "return_code": e.returncode,
                    "stderr": (e.stderr or "")[:1000],
                },
            )
            raise ConversionError(
                "Ghostscript could not convert this PDF to PDF/A.",
                context=context,
            ) from e

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 400:
            raise ConversionError(
                "PDF/A conversion produced an empty file.", context=context
            )

        _verify_pdfa(output_path, expected_part, context)
        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected PDF/A error",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError("Unexpected error: %s" % e, context=context) from e
