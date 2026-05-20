"""Tests for the premium HEIC → JPG/PNG/PDF converter.

Covers:
- utils.convert_heic() format coverage (JPEG, PNG, PDF) — unit-level.
- ConvertHEICAPIView premium gate: anon 403, free 403, premium 200.
- Output content types and file headers.
- Frontend landing page renders successfully (200, key copy present).
"""

from __future__ import annotations

import io
from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from src.users.models import User


def _make_heic_bytes(
    size: tuple[int, int] = (160, 120), colour: tuple[int, int, int] = (255, 0, 0)
) -> bytes:
    """Encode a tiny solid-colour HEIC in-memory using pillow-heif.

    pillow-heif must be registered before this is called (it's auto-registered
    at import time inside `convert_heic.utils`).
    """
    import pillow_heif

    pillow_heif.register_heif_opener()
    im = Image.new("RGB", size, colour)
    buf = io.BytesIO()
    im.save(buf, "HEIF", quality=80)
    buf.seek(0)
    return buf.getvalue()


def _read_streaming(response) -> bytes:
    """Return the response body whether it's a FileResponse or a normal Response."""
    if hasattr(response, "streaming_content"):
        return b"".join(response.streaming_content)
    return response.content


class ConvertHEICUtilsTests(TestCase):
    """Unit tests for the conversion utility itself."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.heic_bytes = _make_heic_bytes()

    def _uploaded(self, name: str = "sample.heic") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, self.heic_bytes, content_type="image/heic")

    def test_convert_to_jpeg_produces_jpg(self):
        from src.api.image_tools.convert_heic.utils import convert_heic

        _, out_path = convert_heic(self._uploaded(), output_format="JPEG")
        self.assertTrue(out_path.endswith(".jpg"))
        with open(out_path, "rb") as fh:
            head = fh.read(3)
        # JPEG magic: FF D8 FF
        self.assertEqual(head[:2], b"\xff\xd8")

    def test_convert_to_png_produces_png(self):
        from src.api.image_tools.convert_heic.utils import convert_heic

        _, out_path = convert_heic(self._uploaded(), output_format="PNG")
        self.assertTrue(out_path.endswith(".png"))
        with open(out_path, "rb") as fh:
            head = fh.read(8)
        self.assertEqual(head, b"\x89PNG\r\n\x1a\n")

    def test_convert_to_pdf_produces_pdf(self):
        from src.api.image_tools.convert_heic.utils import convert_heic

        _, out_path = convert_heic(self._uploaded(), output_format="PDF")
        self.assertTrue(out_path.endswith(".pdf"))
        with open(out_path, "rb") as fh:
            head = fh.read(5)
        self.assertEqual(head, b"%PDF-")

    def test_jpg_alias_accepted(self):
        from src.api.image_tools.convert_heic.utils import convert_heic

        _, out_path = convert_heic(self._uploaded(), output_format="JPG")
        self.assertTrue(out_path.endswith(".jpg"))

    def test_unsupported_format_raises(self):
        from src.api.image_tools.convert_heic.utils import convert_heic

        with self.assertRaises(ValueError):
            convert_heic(self._uploaded(), output_format="WEBP")


@override_settings(
    PAYMENTS_ENABLED=True,
    RATELIMIT_ENABLE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ConvertHEICAPITests(TestCase):
    """End-to-end premium-gating + happy-path API tests."""

    URL = "/api/image/heic-convert/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.heic_bytes = _make_heic_bytes()

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        # Browser-shaped Referer satisfies CaptchaRequirementMiddleware so the
        # spam-protection gate doesn't reject test requests with 400 captcha_required.
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"
        self.free_user = User.objects.create_user(
            email="heic_free@t.test", password="passw0rd!"
        )
        self.premium_user = User.objects.create_user(
            email="heic_premium@t.test", password="passw0rd!"
        )
        # Direct activation — bypass webhook fixtures, this test isn't about LS.
        self.premium_user.is_premium = True
        self.premium_user.subscription_end_date = timezone.now() + timedelta(days=30)
        self.premium_user.save()
        cache.delete(f"user_premium_active:{self.premium_user.pk}")

    def _upload(self, name: str = "sample.heic") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, self.heic_bytes, content_type="image/heic")

    def test_anon_blocked_with_premium_error(self):
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload(), "output_format": "JPEG"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("premium", response.json().get("error", "").lower())

    def test_free_user_blocked_with_premium_error(self):
        self.client.force_authenticate(self.free_user)
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload(), "output_format": "JPEG"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("premium", response.json().get("error", "").lower())

    def test_premium_user_can_convert_to_jpeg(self):
        self.client.force_authenticate(self.premium_user)
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload(), "output_format": "JPEG"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        body = _read_streaming(response)
        self.assertGreater(len(body), 0)
        self.assertEqual(body[:2], b"\xff\xd8")

    def test_premium_user_can_convert_to_png(self):
        self.client.force_authenticate(self.premium_user)
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload(), "output_format": "PNG"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        body = _read_streaming(response)
        self.assertEqual(body[:8], b"\x89PNG\r\n\x1a\n")

    def test_premium_user_can_convert_to_pdf(self):
        self.client.force_authenticate(self.premium_user)
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload(), "output_format": "PDF"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        body = _read_streaming(response)
        self.assertEqual(body[:5], b"%PDF-")

    def test_default_output_format_is_jpeg(self):
        self.client.force_authenticate(self.premium_user)
        response = self.client.post(
            self.URL,
            data={"image_file": self._upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_non_heic_extension_rejected(self):
        self.client.force_authenticate(self.premium_user)
        bad_file = SimpleUploadedFile(
            "sample.png",
            self.heic_bytes,
            content_type="image/png",
        )
        response = self.client.post(
            self.URL,
            data={"image_file": bad_file, "output_format": "JPEG"},
            format="multipart",
        )
        # BaseConversionAPIView returns 400 for disallowed extensions.
        self.assertEqual(response.status_code, 400)


class HEICFrontendPageTests(TestCase):
    """Confirm the public landing page renders with key SEO copy in EN + RU."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_heic_page_renders_english(self):
        response = self.client.get("/en/image/heic-to-jpg/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"HEIC to JPG", response.content)
        self.assertIn(b"Premium Feature", response.content)

    def test_heic_page_renders_russian(self):
        response = self.client.get("/ru/image/heic-to-jpg/", follow=True)
        self.assertEqual(response.status_code, 200)
        # The brand token "HEIC" appears in every locale (kept as Latin in
        # all 7 translations). We don't assert on Cyrillic copy here because
        # CI doesn't run `compilemessages`, so Django falls back to msgid
        # on /ru/ — the translated strings only render when .mo files exist.
        self.assertIn(b"HEIC", response.content)

    def test_heic_page_in_sitemap(self):
        response = self.client.get("/sitemap-en.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/image/heic-to-jpg/", response.content)

    def test_heic_card_in_all_tools(self):
        response = self.client.get("/en/all-tools/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/image/heic-to-jpg/", response.content)

    def test_heic_card_in_premium_tools(self):
        response = self.client.get("/en/premium-tools/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/image/heic-to-jpg/", response.content)

    def test_heic_url_reversal(self):
        url = reverse("frontend:heic_to_jpg_page")
        # i18n_patterns prefixes the active language code; the suffix is what
        # we care about.
        self.assertTrue(url.endswith("/image/heic-to-jpg/"), url)
