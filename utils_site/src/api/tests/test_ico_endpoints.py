"""End-to-end API tests for the favicon/ICO endpoints."""

from __future__ import annotations

import io
import zipfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image


def _png(name="logo.png", size=(256, 256)):
    buf = io.BytesIO()
    Image.new("RGBA", size, (10, 120, 200, 255)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _ico(name="favicon.ico"):
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (200, 30, 30, 255)).save(
        buf, format="ICO", sizes=[(16, 16), (32, 32), (64, 64)]
    )
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/x-icon")


def _read_body(resp):
    if hasattr(resp, "streaming_content"):
        return b"".join(resp.streaming_content)
    return resp.content


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ICOEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        # Browser-shaped Referer satisfies the captcha/spam middleware.
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    def test_image_to_ico_endpoint(self):
        resp = self.client.post(
            "/api/image/to-ico/", {"image_file": _png(), "sizes": "16,32,48"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/x-icon")

    def test_generate_favicon_endpoint_returns_zip(self):
        resp = self.client.post("/api/image/favicon/", {"image_file": _png()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/zip")
        body = _read_body(resp)
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            self.assertIn("favicon.ico", zf.namelist())

    def test_ico_to_png_endpoint(self):
        resp = self.client.post("/api/image/ico-to-png/", {"ico_file": _ico()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/png")
