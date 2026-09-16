"""Regression tests for pdf_to_jpg rendering edge cases (CONVERTICA-5D).

When poppler's own page count (via ``pdfinfo``) disagrees with pypdf's, the
page range handed to ``pdf2image.convert_from_path`` can collapse to empty and
the call returns ``[]`` WITHOUT raising. The conversion util must treat that as
bad input (``InvalidPDFError``) so the Celery task does not pointlessly retry a
file poppler can never render — the retries are what flooded Sentry with 11
events for a single upload.
"""

import os
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_convert.pdf_to_jpg.utils import convert_pdf_to_jpg_sequential
from src.exceptions import InvalidPDFError
from src.tasks.pdf_conversion import _is_user_input_error

_MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF"""


class PdfToJpgEmptyRenderTests(SimpleTestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_pdf2jpg_")
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_render_raises_invalid_pdf_error(self):
        """convert_from_path returning [] (no exception) => InvalidPDFError."""
        uploaded = SimpleUploadedFile(
            "foto1.pdf", _MINIMAL_PDF, content_type="application/pdf"
        )

        # Simulate poppler rendering zero pages while pypdf reports one page.
        with patch("pdf2image.convert_from_path", return_value=[]), self.assertRaises(
            InvalidPDFError
        ) as ctx:
            convert_pdf_to_jpg_sequential(
                uploaded, pages="all", dpi=400, tmp_dir=self.tmp_dir
            )

        # The message must be classified as a user-fixable input error so the
        # Celery task does NOT retry (no retries => no Sentry amplification).
        self.assertTrue(
            _is_user_input_error(ctx.exception),
            f"message not recognized as user input error: {ctx.exception}",
        )

    def test_no_stray_zip_left_on_empty_render(self):
        """A failed render must not leave a half-written output ZIP behind."""
        uploaded = SimpleUploadedFile(
            "foto1.pdf", _MINIMAL_PDF, content_type="application/pdf"
        )
        with patch("pdf2image.convert_from_path", return_value=[]), self.assertRaises(
            InvalidPDFError
        ):
            convert_pdf_to_jpg_sequential(
                uploaded, pages="all", dpi=400, tmp_dir=self.tmp_dir
            )

        zips = [f for f in os.listdir(self.tmp_dir) if f.endswith(".zip")]
        self.assertEqual(zips, [], f"stray zip left behind: {zips}")

    def test_malformed_page_input_raises_invalid_not_500(self):
        """Bad `pages` strings must raise InvalidPDFError (→4xx), never a bare
        ValueError (→500) or an index-(-1) render. Valid forms still parse."""
        for bad in ("1-", "-5", "1-5-9", "abc", "a-b", ""):
            uploaded = SimpleUploadedFile(
                "foto1.pdf", _MINIMAL_PDF, content_type="application/pdf"
            )
            with self.assertRaises(InvalidPDFError, msg=f"pages={bad!r}"):
                convert_pdf_to_jpg_sequential(
                    uploaded, pages=bad, dpi=72, tmp_dir=self.tmp_dir
                )
