"""Output PDF validation for Word->PDF (CONVERTICA audit Sec-2).

The unoserver fast path (and subprocess fallback) validated output only with a
file_size==0 check, so a truncated/partial PDF (valid %PDF- header, no xref/EOF)
was returned to the user as a successful conversion. Validate the PDF actually
opens and has >=1 page.
"""

from __future__ import annotations

import io
import os
import tempfile

from django.test import SimpleTestCase
from src.api.pdf_convert.word_to_pdf_optimized import _validate_output_pdf
from src.exceptions import ConversionError


def _write(data: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


class ValidateOutputPdfTests(SimpleTestCase):
    def test_empty_file_raises(self):
        with self.assertRaises(ConversionError):
            _validate_output_pdf(_write(b""))

    def test_truncated_pdf_raises(self):
        # Valid header but garbage/no xref — pypdf cannot parse pages.
        with self.assertRaises(ConversionError):
            _validate_output_pdf(_write(b"%PDF-1.4\nthis is not a real pdf body"))

    def test_valid_single_page_pdf_passes(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        # Should not raise.
        _validate_output_pdf(_write(buf.getvalue()))
