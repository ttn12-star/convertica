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


class PdfToExcelPageCacheTests(TestCase):
    def test_parsed_pages_are_not_kept_alive(self):
        # Without flush_cache pdfplumber kept every parsed page alive: 200 pages
        # peaked at ~900 MB in a celery child sharing 2G with two others.
        # 40 pages: ~120 MB traced without the fix, ~16 MB with it.
        import tracemalloc

        from src.api.pdf_convert.pdf_to_excel.utils import convert_pdf_to_excel

        upload = SimpleUploadedFile(
            "t.pdf", _text_pdf(pages=40), content_type="application/pdf"
        )
        tracemalloc.start()
        try:
            convert_pdf_to_excel(upload)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 50 * 1024 * 1024)


def _sideways_phone_jpeg() -> bytes:
    # Landscape pixels + Orientation=6: a portrait photo as phones store it.
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (800, 400), (200, 30, 30))
    exif = img.getexif()
    exif[0x0112] = 6
    buf = BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


class JpgToPdfExifOrientationTests(TestCase):
    def _placed_image_is_portrait(self, pdf_path: str) -> bool:
        with fitz.open(pdf_path) as doc:
            x0, y0, x1, y1 = doc[0].get_image_info()[0]["bbox"]
        return (y1 - y0) > (x1 - x0)

    def test_phone_photo_is_upright_on_every_path_and_quality(self):
        import asyncio

        from src.api.pdf_convert.jpg_to_pdf.utils import _convert_jpg_to_pdf_sequential
        from src.api.pdf_convert.jpg_to_pdf_optimized import (
            convert_jpg_to_pdf_optimized,
        )

        for name, convert in (
            ("sequential", _convert_jpg_to_pdf_sequential),
            ("optimized", convert_jpg_to_pdf_optimized),
        ):
            for quality in (85, 95):
                upload = SimpleUploadedFile("p.jpg", _sideways_phone_jpeg())
                _, pdf = asyncio.new_event_loop().run_until_complete(
                    convert(upload, quality=quality)
                )
                self.assertTrue(
                    self._placed_image_is_portrait(pdf), f"{name} q{quality}"
                )
