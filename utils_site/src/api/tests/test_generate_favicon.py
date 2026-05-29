"""Tests for the favicon-package generator util."""

from __future__ import annotations

import io
import json
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image


def _png_upload(size=(512, 512), name="brand.png") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGBA", size, (20, 80, 160, 255)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


EXPECTED_MEMBERS = {
    "favicon.ico",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon-48x48.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "site.webmanifest",
    "snippet.html",
}


class GenerateFaviconTests(TestCase):
    def test_zip_contains_all_members(self):
        from src.api.image_tools.generate_favicon.utils import generate_favicon

        _, output_path = generate_favicon(_png_upload())
        self.assertTrue(output_path.endswith(".zip"))
        with zipfile.ZipFile(output_path) as zf:
            names = set(zf.namelist())
            self.assertEqual(names, EXPECTED_MEMBERS)
            manifest = json.loads(zf.read("site.webmanifest"))
            self.assertIn("icons", manifest)
            self.assertTrue(len(manifest["icons"]) >= 2)
            snippet = zf.read("snippet.html").decode("utf-8")
            self.assertIn("apple-touch-icon", snippet)
            self.assertIn("site.webmanifest", snippet)

    def test_apple_touch_icon_is_180px(self):
        from src.api.image_tools.generate_favicon.utils import generate_favicon

        _, output_path = generate_favicon(_png_upload())
        with zipfile.ZipFile(output_path) as zf, Image.open(
            io.BytesIO(zf.read("apple-touch-icon.png"))
        ) as img:
            self.assertEqual(img.size, (180, 180))
