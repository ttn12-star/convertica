"""Tests for the ICO-to-PNG converter util."""

from __future__ import annotations

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image


def _ico_upload(name="favicon.ico") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (200, 30, 30, 255)).save(
        buf, format="ICO", sizes=[(16, 16), (32, 32), (64, 64)]
    )
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/x-icon")


class ICOToPNGTests(TestCase):
    def test_extracts_largest_frame_as_png(self):
        from src.api.image_tools.ico_to_png.utils import ico_to_png

        _, output_path = ico_to_png(_ico_upload())
        self.assertTrue(output_path.endswith(".png"))
        with Image.open(output_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (64, 64))
