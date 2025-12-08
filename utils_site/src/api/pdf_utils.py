# Shared PDF utilities
import os
from typing import Optional

import fitz  # PyMuPDF

from .logging_utils import get_logger

logger = get_logger(__name__)


def repair_pdf(input_path: str, output_path: Optional[str] = None) -> str:
    """Attempt to repair a potentially corrupted PDF file.

    Uses PyMuPDF to open and re-save the PDF with garbage collection,
    which can fix issues like broken xref tables and invalid object references.

    Args:
        input_path: Path to the original PDF file
        output_path: Path to save the repaired PDF. If None, repairs in-place.

    Returns:
        Path to the repaired PDF (output_path or input_path if in-place)

    Raises:
        Exception: If repair fails completely
    """
    if output_path is None:
        output_path = input_path

    try:
        # Open PDF (PyMuPDF automatically attempts basic repair on open)
        doc = fitz.open(input_path)

        # Re-save with maximum garbage collection and compression
        # garbage=4 removes unused objects and compacts xref
        # deflate=True compresses streams
        # clean=True sanitizes content streams
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True,
        )
        doc.close()

        logger.debug("PDF repair successful: %s -> %s", input_path, output_path)
        return output_path

    except Exception as e:
        logger.warning("PDF repair failed for %s: %s", input_path, e)
        # If repair fails, return original path - let the caller handle the error
        return input_path


def open_pdf_safe(pdf_path: str, repair: bool = True) -> fitz.Document:
    """Open a PDF file safely, optionally repairing it first.

    Args:
        pdf_path: Path to the PDF file
        repair: Whether to attempt repair before opening

    Returns:
        PyMuPDF Document object
    """
    if repair:
        # Create a temporary repaired version
        tmp_dir = os.path.dirname(pdf_path)
        base_name = os.path.basename(pdf_path)
        repaired_path = os.path.join(tmp_dir, f"_repaired_{base_name}")

        try:
            repair_pdf(pdf_path, repaired_path)
            if os.path.exists(repaired_path):
                doc = fitz.open(repaired_path)
                # Clean up repaired file after opening
                try:
                    os.remove(repaired_path)
                except OSError:
                    pass
                return doc
        except Exception:
            pass  # Fall through to normal open

    return fitz.open(pdf_path)
