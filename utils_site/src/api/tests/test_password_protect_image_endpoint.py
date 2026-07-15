"""Endpoint tests for the password-protect-image API (single-file route).

Covers:
- Valid image + password -> 200, application/pdf, and the PDF is genuinely
  AES-256 encrypted (decrypts with the right password).
- Missing password -> observed status (documented below).
- Non-image bytes upload -> observed status (documented below).

CAPTCHA/spam-protection bypass mirrors ConvertHEICAPITests
(src/api/tests/test_convert_heic.py): BaseConversionAPIView.post_async()
runs validate_spam_protection() first, which is satisfied by a
browser-shaped Referer header via CaptchaRequirementMiddleware.
"""

from __future__ import annotations

from io import BytesIO

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader
from rest_framework.test import APIClient


def _png_upload(color="red", size=(100, 100), name="photo.png"):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    buf.name = name
    return buf


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class PasswordProtectImageEndpointTests(TestCase):
    URL_NAME = "password_protect_image_api"

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        # Browser-shaped Referer satisfies CaptchaRequirementMiddleware so the
        # spam-protection gate doesn't reject anonymous test requests with a
        # 400 captcha_required (same bypass as ConvertHEICAPITests).
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    def test_single_image_returns_encrypted_pdf(self):
        response = self.client.post(
            reverse(self.URL_NAME),
            data={"image_files": _png_upload(), "password": "s3cret"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        body = b"".join(response.streaming_content)
        reader = PdfReader(BytesIO(body))
        self.assertTrue(reader.is_encrypted)
        self.assertTrue(reader.decrypt("s3cret"))

    def test_missing_password_rejected(self):
        # OBSERVED: the serializer marks `password` required (min_length=1),
        # so BaseConversionAPIView.post_async() fails serializer.is_valid()
        # and returns 400 before perform_conversion() ever runs.
        response = self.client.post(
            reverse(self.URL_NAME),
            data={"image_files": _png_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_password_rejected(self):
        # Same path as above: CharField(min_length=1) rejects "".
        response = self.client.post(
            reverse(self.URL_NAME),
            data={"image_files": _png_upload(), "password": ""},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_image_rejected(self):
        # OBSERVED: non-image bytes (padded past validate_file_basic()'s
        # 100-byte minimum-size check, otherwise it's masked as a 400 "file
        # too small" instead of the case under test) pass the extension /
        # content-type checks (both say "photo.png" / image/png), so
        # perform_conversion() runs and protect_image() raises ConversionError
        # when Image.open(...).verify() fails. base_views.py's generic error
        # handler maps ConversionError -> HTTP_500_INTERNAL_SERVER_ERROR (not
        # 400) — flagged in the task brief as a real gap, not a test bug.
        buf = BytesIO(b"this is not an image" * 10)
        buf.name = "photo.png"
        response = self.client.post(
            reverse(self.URL_NAME),
            data={"image_files": buf, "password": "s3cret"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 500)
