import io
import os
import random

import fitz
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from PIL import Image
from rest_framework.test import APIClient
from src.api.pdf_organize.compress_pdf.utils import compress_pdf


def _scan_pdf(pages=3) -> bytes:
    """Photo-like pages: big noisy JPEGs, the kind portals reject as too large."""
    random.seed(7)
    doc = fitz.open()
    for i in range(pages):
        im = Image.effect_noise((400, 560), 50).convert("RGB").resize((1600, 2240))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=95)
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=buf.getvalue())
        page.insert_text((50, 60), f"Page {i + 1}", fontsize=14)
    return doc.tobytes()


def _compress(raw: bytes, **kw) -> tuple[int, fitz.Document]:
    _, out = compress_pdf(
        SimpleUploadedFile("scan.pdf", raw, content_type="application/pdf"),
        compression_level="medium",
        **kw,
    )
    return os.path.getsize(out), fitz.open(out)


class CompressTargetSizeTests(SimpleTestCase):
    def test_target_is_met_when_reachable_and_best_effort_otherwise(self):
        raw = _scan_pdf()
        plain, _ = _compress(raw)
        target_kb = plain // 1024 // 3  # well below what the level alone gives
        size, doc = _compress(raw, target_size_kb=target_kb)
        self.assertLessEqual(size, target_kb * 1024)
        self.assertEqual(len(doc), 3)
        self.assertIn("Page 3", doc[2].get_text())

        tiny, doc = _compress(raw, target_size_kb=20)  # not reachable
        self.assertGreater(tiny, 20 * 1024)
        self.assertLessEqual(tiny, plain)  # never worse than no target
        self.assertEqual(len(doc), 3)

    def test_no_time_left_keeps_the_plain_result(self):
        # The page posts synchronously; a slow scan must not run past
        # Cloudflare's 100 s, so the search yields when the budget is spent.
        from unittest import mock

        from src.api.pdf_organize.compress_pdf import utils

        raw = _scan_pdf()
        plain, _ = _compress(raw)
        target_kb = plain // 1024 // 3
        with mock.patch.object(utils, "TARGET_TIME_BUDGET", 0):
            size, _ = _compress(raw, target_size_kb=target_kb)
        # No step ran: still well above the target, i.e. the plain result
        # (byte counts can wobble a little between saves, hence no equality).
        self.assertGreater(size, target_kb * 1024 * 2)
        self.assertAlmostEqual(size, plain, delta=max(2048, plain // 100))


class CompressTargetApiTests(TestCase):
    def test_api_reports_whether_the_target_was_met(self):
        cache.clear()
        raw = _scan_pdf(2)
        for target, met in (("300", "true"), ("20", "false")):
            response = APIClient().post(
                "/api/pdf-organize/compress/",
                {
                    "pdf_file": SimpleUploadedFile(
                        "s.pdf", raw, content_type="application/pdf"
                    ),
                    "target_size_kb": target,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["X-Target-Size-Kb"], target)
            self.assertEqual(response["X-Target-Met"], met)
        bad = APIClient().post(
            "/api/pdf-organize/compress/",
            {
                "pdf_file": SimpleUploadedFile("s.pdf", raw),
                "target_size_kb": "5",
            },
        )
        self.assertEqual(bad.status_code, 400)  # below the 20 KB floor
