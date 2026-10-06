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

    def test_text_exports_named_doc_still_pass_and_binary_junk_does_not(self):
        # "Export to Word" from 1C/banks/CRMs writes HTML, RTF or WordML under
        # a .doc name; LibreOffice converts them with its text filters. Only
        # binary content without ZIP/OLE magic is the CVE-shaped input.
        import tempfile

        from src.api.file_validation import validate_word_file

        cases = {
            b"{\\rtf1\\ansi Hello}" * 20: True,
            b"\xef\xbb\xbf{\\rtf1 BOM}" * 20: True,
            "<html><p>Привет</p></html>".encode("cp1251") * 20: True,
            b'<?xml version="1.0"?><w:wordDocument/>': True,
            os.urandom(4000): False,
        }
        for data, expected in cases.items():
            with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as f:
                f.write(data)
            try:
                self.assertEqual(validate_word_file(f.name, {})[0], expected, data[:20])
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


class WordLibreOfficeRetryTests(TestCase):
    """One LibreOffice run per conversion; retry only a crashed soffice."""

    def _run(self, side_effect):
        import asyncio
        import tempfile
        from unittest import mock

        from src.api.pdf_convert.word_to_pdf_optimized import (
            OptimizedWordToPDFConverter,
        )

        tmp = tempfile.mkdtemp()
        docx, pdf = os.path.join(tmp, "a.docx"), os.path.join(tmp, "a.pdf")
        with (
            mock.patch("shutil.which", return_value="/usr/bin/libreoffice"),
            mock.patch(
                "src.api.pdf_convert.word_to_pdf_optimized._run_libreoffice",
                side_effect=side_effect,
            ) as run,
            mock.patch("asyncio.sleep"),
        ):
            try:
                asyncio.new_event_loop().run_until_complete(
                    OptimizedWordToPDFConverter()._convert_with_libreoffice_async(
                        docx, pdf, {}
                    )
                )
                return run, None, tmp
            except Exception as e:  # noqa: BLE001 - the test inspects it
                return run, e, tmp

    def test_good_file_is_one_run_without_infilter(self):
        def ok(cmd, env, timeout):
            open(os.path.join(os.path.dirname(cmd[-1]), "a.pdf"), "wb").close()

        run, err, _ = self._run(ok)
        self.assertIsNone(err)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(any("infilter" in a for a in run.call_args[0][0]))

    def test_unopenable_file_is_400_after_one_run(self):
        from src.exceptions import InvalidPDFError

        run, err, _ = self._run(lambda *a: None)  # rc=0, no PDF
        self.assertIsInstance(err, InvalidPDFError)
        self.assertEqual(run.call_count, 1)

    def test_oom_kill_and_timeout_are_not_retried(self):
        import subprocess

        from src.exceptions import ConversionError

        for exc in (
            subprocess.CalledProcessError(-9, ["libreoffice"], stderr=b""),
            subprocess.TimeoutExpired(["libreoffice"], 180),
        ):
            run, err, _ = self._run(exc)
            self.assertIsInstance(err, ConversionError)
            self.assertEqual(run.call_count, 1, type(exc).__name__)

    def test_crashed_soffice_is_retried(self):
        import subprocess

        run, err, _ = self._run(
            subprocess.CalledProcessError(1, ["libreoffice"], stderr=b"crash")
        )
        self.assertIsNotNone(err)
        self.assertEqual(run.call_count, 3)


class ExcelPptTimeoutNotRetriedTests(TestCase):
    def test_timeout_is_one_run(self):
        import asyncio
        import subprocess
        from unittest import mock

        from src.api.pdf_convert.excel_to_pdf.utils import ExcelToPDFConverter
        from src.api.pdf_convert.ppt_to_pdf.utils import PowerPointToPDFConverter
        from src.exceptions import ConversionError

        for module, conv in (
            ("excel_to_pdf", ExcelToPDFConverter()),
            ("ppt_to_pdf", PowerPointToPDFConverter()),
        ):
            with (
                mock.patch("shutil.which", return_value="/usr/bin/libreoffice"),
                mock.patch(
                    f"src.api.pdf_convert.{module}.utils._run_libreoffice",
                    side_effect=subprocess.TimeoutExpired(["libreoffice"], 1),
                ) as run,
                mock.patch("asyncio.sleep"),
                self.assertRaises(ConversionError),
            ):
                asyncio.new_event_loop().run_until_complete(
                    conv._convert_with_libreoffice_async("/tmp/x.in", "/tmp/x.pdf", {})
                )
            self.assertEqual(run.call_count, 1, module)


class OcrSkewDetectionTests(TestCase):
    def test_angle_is_found_on_a_downscaled_copy(self):
        # 22 full-size rotations of a 300 DPI A4 scan took ~3.5 s per page.
        from unittest import mock

        from PIL import Image, ImageDraw
        from scipy import ndimage
        from src.api import ocr_utils

        img = Image.new("L", (2480, 3508), 255)
        draw = ImageDraw.Draw(img)
        for y in range(200, 3300, 60):
            draw.rectangle((200, y, 2200, y + 20), fill=0)
        img = img.rotate(2, fillcolor=255)

        with mock.patch.object(
            ocr_utils.ndimage, "rotate", wraps=ndimage.rotate
        ) as rotate:
            angle = ocr_utils.detect_skew_angle(img)
        self.assertEqual(angle, -2.0)
        self.assertLessEqual(max(rotate.call_args[0][0].shape), 1000)


class PdfToHtmlEscapingTests(TestCase):
    def test_pdf_text_cannot_inject_markup(self):
        from src.api.pdf_convert.pdf_to_html.utils import convert_pdf_to_html

        doc = fitz.open()
        doc.new_page().insert_text((50, 60), "a < b <script>alert(1)</script>")
        upload = SimpleUploadedFile("x.pdf", doc.tobytes(), "application/pdf")
        _, out = convert_pdf_to_html(upload, extract_images=False)
        with open(out, encoding="utf-8") as f:
            page = f.read()
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)


class CeleryDoesNotReplayHopelessFailuresTests(TestCase):
    """The async path (the front end's main one) re-ran the whole conversion
    twice on a damaged file, an OOM kill or a timeout: the converter's own
    'do not retry' never reached the task's retry decision."""

    def _run_task(self, exc):
        import tempfile
        from unittest import mock

        from celery.exceptions import Retry
        from src.tasks.pdf_conversion import generic_conversion_task

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "a.docx")
        with open(path, "wb") as f:
            f.write(b"PK\x03\x04x")
        with (
            mock.patch(
                "src.api.optimization_manager.optimization_manager.convert_word_to_pdf",
                side_effect=exc,
            ),
            mock.patch.object(
                generic_conversion_task, "retry", side_effect=Retry("retry")
            ) as retry,
        ):
            result = generic_conversion_task.apply(
                args=("t-" + os.path.basename(tmp), path, "a.docx", "word_to_pdf")
            )
        return retry.call_count, result.result

    def test_damaged_file_oom_and_timeout_are_not_retried(self):
        from src.exceptions import ConversionError, InvalidPDFError

        oom = ConversionError("LibreOffice conversion failed: the file is too large")
        oom.retryable = False
        for exc in (InvalidPDFError("The document could not be opened."), oom):
            retries, result = self._run_task(exc)
            self.assertEqual(retries, 0, exc)
            self.assertEqual(result["status"], "error")

    def test_transient_failure_is_still_retried(self):
        from src.exceptions import ConversionError

        retries, _ = self._run_task(ConversionError("soffice crashed"))
        self.assertEqual(retries, 1)
