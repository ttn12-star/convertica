"""JPG to PDF must produce the same paper size whichever code path runs.

There are three: the optimized converter, the sequential fallback, and the
multi-file branch in the view. They used to disagree — the optimized one
defaulted to US Letter while the other two hardcoded A4 — so the sheet a user
got depended on file size and on which branch happened to handle the upload.
Nothing passed the parameter, so nobody could choose either.
"""

from __future__ import annotations

import asyncio
import inspect

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from src.api.pdf_convert.jpg_to_pdf import views as jpg_views
from src.api.pdf_convert.jpg_to_pdf.serializers import JPGToPDFSerializer
from src.api.pdf_convert.jpg_to_pdf.utils import _convert_jpg_to_pdf_sequential
from src.api.pdf_convert.jpg_to_pdf_optimized import convert_jpg_to_pdf_optimized

MM = 72 / 25.4
A4_SIZE = (210 * MM, 297 * MM)
LETTER_SIZE = (215.9 * MM, 279.4 * MM)


def _jpg_upload(name: str = "photo.jpg") -> SimpleUploadedFile:
    import io

    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 120, 60)).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _page_size(pdf_path: str) -> tuple[float, float]:
    doc = fitz.open(pdf_path)
    try:
        return doc[0].rect.width, doc[0].rect.height
    finally:
        doc.close()


class JPGToPDFPageSizeTests(TestCase):
    def test_default_is_a4_on_the_sequential_path(self):
        _, out = asyncio.run(_convert_jpg_to_pdf_sequential(_jpg_upload()))
        width, height = _page_size(out)
        self.assertAlmostEqual(width, A4_SIZE[0], delta=1.0)
        self.assertAlmostEqual(height, A4_SIZE[1], delta=1.0)

    def test_letter_is_honoured_on_the_sequential_path(self):
        _, out = asyncio.run(
            _convert_jpg_to_pdf_sequential(_jpg_upload(), page_size="letter")
        )
        width, height = _page_size(out)
        self.assertAlmostEqual(width, LETTER_SIZE[0], delta=1.0)
        self.assertAlmostEqual(height, LETTER_SIZE[1], delta=1.0)

    def test_all_three_paths_share_the_same_default(self):
        """The actual regression: the paths must not disagree on the sheet."""
        defaults = {
            "serializer": JPGToPDFSerializer().fields["page_size"].default,
            "sequential": inspect.signature(_convert_jpg_to_pdf_sequential)
            .parameters["page_size"]
            .default,
            "optimized": inspect.signature(convert_jpg_to_pdf_optimized)
            .parameters["page_size"]
            .default,
        }
        self.assertEqual(set(defaults.values()), {"a4"}, defaults)

    def test_multi_file_branch_reads_the_parameter(self):
        """The view's multi-file branch must not hardcode a sheet either."""
        source = inspect.getsource(jpg_views)
        self.assertIn('request.POST.get("page_size"', source)
