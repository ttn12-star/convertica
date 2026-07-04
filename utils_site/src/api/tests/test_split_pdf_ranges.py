"""Regression tests for split_pdf page/range edge cases.

Guards two bugs found in audit:
- "page" mode given a range like "2-3" parsed to an empty selection, hit the
  written==0 PyMuPDF fallback and split the WHOLE document.
- "range" mode with a reversed/out-of-range range ("5-1") wrote a 0-page PDF
  into the zip and reported success.
"""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from reportlab.pdfgen import canvas
from src.api.pdf_organize.split_pdf.utils import split_pdf
from src.exceptions import InvalidPDFError


def _make_pdf(pages: int) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(72, 72, f"page {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def _upload(pages: int) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "doc.pdf", _make_pdf(pages), content_type="application/pdf"
    )


def _zip_members(zip_path: str) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.namelist()


class SplitPdfRangeTests(SimpleTestCase):
    def test_page_mode_range_input_does_not_split_whole_doc(self):
        # "2-3" is a range, invalid in page mode — must raise, NOT split all 5.
        with self.assertRaises(InvalidPDFError):
            split_pdf(_upload(5), split_type="page", pages="2-3")

    def test_range_mode_reversed_range_raises_not_zero_page_pdf(self):
        with self.assertRaises(InvalidPDFError):
            split_pdf(_upload(5), split_type="range", pages="5-1")

    def test_range_mode_out_of_range_raises(self):
        with self.assertRaises(InvalidPDFError):
            split_pdf(_upload(5), split_type="range", pages="99-100")

    def test_valid_range_still_works(self):
        _tmp, zip_path = split_pdf(_upload(5), split_type="range", pages="2-3")
        members = _zip_members(zip_path)
        self.assertEqual(len(members), 1, members)

    def test_valid_page_selection_still_works(self):
        _tmp, zip_path = split_pdf(_upload(5), split_type="page", pages="1,3")
        members = _zip_members(zip_path)
        self.assertEqual(len(members), 2, members)
