"""Tests for the Image to Text (OCR) tool: OCR core refactor, API, and page."""

from __future__ import annotations

import io
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image


def _png_bytes(size=(120, 60), colour=(255, 255, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    buf.seek(0)
    return buf.getvalue()


# A fake pytesseract image_to_data DICT: two lines in one paragraph, then a
# second paragraph; one low-confidence word that must be dropped.
FAKE_OCR_DATA = {
    "text": ["Invoice", "2026", "lowconf", "Total", "42", "Thanks"],
    "conf": ["96", "95", "12", "90", "88", "70"],
    "block_num": [1, 1, 1, 1, 1, 2],
    "par_num": [1, 1, 1, 1, 1, 1],
    "line_num": [1, 1, 1, 2, 2, 1],
}


class ReconstructTextTests(TestCase):
    def test_groups_lines_and_paragraphs_and_filters_confidence(self):
        from src.api.ocr_utils import _reconstruct_text_from_ocr_data

        result = _reconstruct_text_from_ocr_data(FAKE_OCR_DATA, confidence_threshold=60)
        # "lowconf" (conf 12) dropped; line 1 and line 2 joined by \n;
        # paragraph/block break -> blank line before "Thanks".
        self.assertEqual(result, "Invoice 2026\nTotal 42\n\nThanks")

    def test_blank_input_returns_empty_string(self):
        from src.api.ocr_utils import _reconstruct_text_from_ocr_data

        empty = {"text": [], "conf": [], "block_num": [], "par_num": [], "line_num": []}
        self.assertEqual(_reconstruct_text_from_ocr_data(empty, 60), "")


class ExtractTextFromImageTests(TestCase):
    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_extract_text_from_image_uses_reconstruction(self, _mock):
        from src.api.ocr_utils import extract_text_from_image

        img = Image.new("RGB", (200, 80), (255, 255, 255))
        result = extract_text_from_image(
            img, user_language="en", confidence_threshold=60
        )
        self.assertEqual(result, "Invoice 2026\nTotal 42\n\nThanks")


class ExtractTextFromPdfRefactorTests(TestCase):
    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    @patch("src.api.ocr_utils.convert_from_path")
    def test_pdf_path_calls_per_image_ocr(self, mock_convert, _mock_ocr):
        from src.api.ocr_utils import extract_text_from_pdf

        mock_convert.return_value = [Image.new("RGB", (200, 80), (255, 255, 255))]
        uploaded = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
        )
        _path, text = extract_text_from_pdf(uploaded, user_language="en")
        self.assertIn("Invoice 2026", text)
        self.assertIn("Thanks", text)


class RunImageOCRTests(TestCase):
    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_writes_txt_with_extracted_text(self, _mock):
        from src.api.image_tools.image_to_text.utils import run_image_ocr

        upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")
        input_path, output_path = run_image_ocr(upload, language="en")
        self.assertTrue(output_path.endswith(".txt"))
        with open(output_path, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("Invoice 2026", body)
        self.assertIn("Thanks", body)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ImageToTextAPITests(TestCase):
    URL = "/api/image/to-text/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        # Browser-shaped Referer satisfies the captcha/spam middleware.
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_anonymous_user_gets_text_plain(self, _mock):
        upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")
        resp = self.client.post(self.URL, data={"image_file": upload})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Type"].startswith("text/plain"))
        body = (
            b"".join(resp.streaming_content)
            if hasattr(resp, "streaming_content")
            else resp.content
        )
        self.assertIn(b"Invoice 2026", body)

    def test_unsupported_extension_rejected(self):
        bad = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4 x", content_type="application/pdf"
        )
        resp = self.client.post(self.URL, data={"image_file": bad})
        self.assertEqual(resp.status_code, 400)

    def test_get_not_allowed(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 405)


class ImageToTextConfigTests(TestCase):
    def test_tool_config_registered(self):
        from src.frontend.tool_configs import TOOL_CONFIGS

        cfg = TOOL_CONFIGS["image_to_text"]
        self.assertEqual(cfg["template"], "frontend/image_tools/image_to_text.html")
        self.assertEqual(cfg["converter_args"]["api_url_name"], "image_to_text_api")
        self.assertEqual(cfg["converter_args"]["file_input_name"], "image_file")


class ImageToTextPageRouteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_url_reversal(self):
        url = reverse("frontend:image_to_text_page")
        self.assertTrue(url.endswith("/image/to-text/"), url)

    def test_page_in_sitemap(self):
        resp = self.client.get("/sitemap-en.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"/image/to-text/", resp.content)


class ImageToTextRenderTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_page_renders_english(self):
        resp = self.client.get("/en/image/to-text/", follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Image to Text", resp.content)
        # Tool-specific controls are present:
        self.assertIn(b"ocrLanguageSelect", resp.content)
        self.assertIn(b"ocrResultPanel", resp.content)
        # The extra_js {% comment %} block must not leak into rendered output
        # (a multi-line {# #} comment would render as visible text).
        self.assertNotIn(b"Config script", resp.content)


class ImageToTextNavTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_link_in_all_tools(self):
        resp = self.client.get("/en/all-tools/", follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"/image/to-text/", resp.content)


@override_settings(
    RATELIMIT_ENABLE=False,
    IMAGE_TO_TEXT_FREE_DAILY=2,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ImageToTextLimitsTests(TestCase):
    """Free-tier limits (size + daily count) and premium .docx export."""

    URL = "/api/image/to-text/"

    def setUp(self):
        from rest_framework.test import APIClient

        cache.clear()
        self.client = APIClient()
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    def _png(self, name="p.png"):
        return SimpleUploadedFile(
            name, _png_bytes(size=(200, 80)), content_type="image/png"
        )

    def _premium_user(self):
        from datetime import timedelta

        from django.utils import timezone
        from src.users.models import User

        u = User.objects.create_user(email="itt_prem@t.test", password="passw0rd!")
        u.is_premium = True
        u.subscription_end_date = timezone.now() + timedelta(days=30)
        u.save()
        cache.delete(f"user_premium_active:{u.pk}")
        return u

    @patch(
        "src.api.spam_protection.check_minimum_time_between_requests",
        return_value=(True, None),
    )
    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_free_daily_limit_then_429(self, _ocr, _timing):
        # _timing patch disables the 2s anti-burst cooldown so we can fire the
        # daily quota back-to-back.
        for _i in range(2):  # IMAGE_TO_TEXT_FREE_DAILY=2
            r = self.client.post(self.URL, data={"image_file": self._png()})
            self.assertEqual(r.status_code, 200)
        r = self.client.post(self.URL, data={"image_file": self._png()})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Premium", r.json().get("error", ""))

    def test_free_docx_blocked_with_upsell(self):
        r = self.client.post(
            self.URL, data={"image_file": self._png(), "output_format": "docx"}
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("Premium", r.json().get("error", ""))

    @override_settings(IMAGE_TO_TEXT_FREE_MAX_BYTES=100)
    def test_free_oversize_blocked(self):
        r = self.client.post(self.URL, data={"image_file": self._png()})
        self.assertEqual(r.status_code, 413)
        self.assertIn("Premium", r.json().get("error", ""))

    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_premium_docx_download(self, _m):
        self.client.force_authenticate(self._premium_user())
        r = self.client.post(
            self.URL, data={"image_file": self._png(), "output_format": "docx"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("wordprocessingml", r["Content-Type"])
        body = (
            b"".join(r.streaming_content)
            if hasattr(r, "streaming_content")
            else r.content
        )
        self.assertEqual(body[:2], b"PK")  # .docx is a zip container

    @patch(
        "src.api.spam_protection.check_minimum_time_between_requests",
        return_value=(True, None),
    )
    @patch("src.api.ocr_utils.pytesseract.image_to_data", return_value=FAKE_OCR_DATA)
    def test_premium_has_no_daily_limit(self, _ocr, _timing):
        self.client.force_authenticate(self._premium_user())
        for _i in range(4):  # well over the free daily cap of 2
            r = self.client.post(self.URL, data={"image_file": self._png()})
            self.assertEqual(r.status_code, 200)
