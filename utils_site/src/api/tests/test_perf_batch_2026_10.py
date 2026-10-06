"""One runnable check per fix from the 2026-10 perf/quality audit (batch 1).

Each test is the smallest thing that fails if the corresponding fix regresses.
"""

import os

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase


def _text_pdf(pages: int = 30) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text(
            (50, 60),
            "\n".join(f"Line {i}-{j} lorem ipsum dolor sit amet" for j in range(50)),
            fontsize=9,
        )
    return doc.tobytes(deflate=False)


class CompressTextPdfTests(TestCase):
    def test_every_level_actually_shrinks_an_uncompressed_text_pdf(self):
        # compression_effort is a 0-100 percentage in MuPDF; 2/6/9 left the
        # rewritten streams nearly raw, the output grew, and the "never return
        # something bigger" guard handed the user back the original file.
        from src.api.pdf_organize.compress_pdf.utils import compress_pdf

        raw = _text_pdf()
        for level in ("low", "medium", "high"):
            upload = SimpleUploadedFile("t.pdf", raw, content_type="application/pdf")
            _, out = compress_pdf(upload, compression_level=level)
            self.assertLess(os.path.getsize(out), len(raw) * 0.7, level)


class WordInputValidationTests(TestCase):
    def test_junk_docx_is_rejected_before_libreoffice(self):
        # validate_word_file was commented out "temporarily for testing", so
        # any bytes named .doc/.docx reached LibreOffice (CVE surface) and a
        # broken file came back as a 500 after three LibreOffice runs.
        import asyncio
        from unittest import mock

        from src.api.pdf_convert.word_to_pdf_optimized import (
            OptimizedWordToPDFConverter,
        )
        from src.exceptions import InvalidPDFError

        upload = SimpleUploadedFile("x.docx", b"PK\x03\x04" + b"junk" * 500)
        conv = OptimizedWordToPDFConverter()
        with (
            mock.patch.object(conv, "_convert_with_libreoffice_async") as lo,
            self.assertRaises(InvalidPDFError),
        ):
            asyncio.new_event_loop().run_until_complete(
                conv.convert_word_to_pdf_optimized(upload)
            )
        lo.assert_not_called()

    def test_rtf_saved_as_doc_still_passes(self):
        import tempfile

        from src.api.file_validation import validate_word_file

        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as f:
            f.write(b"{\\rtf1\\ansi Hello}")
        try:
            self.assertEqual(validate_word_file(f.name, {}), (True, None))
        finally:
            os.unlink(f.name)
