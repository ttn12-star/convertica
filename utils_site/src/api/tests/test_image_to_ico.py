"""Tests for the image-to-ICO converter util."""

from __future__ import annotations

import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image


def _png_upload(
    size=(256, 256), colour=(10, 120, 200), name="logo.png"
) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGBA", size, colour + (255,)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class ImageToICOTests(TestCase):
    def test_produces_multi_resolution_ico(self):
        from src.api.image_tools.image_to_ico.utils import image_to_ico

        input_path, output_path = image_to_ico(_png_upload(), sizes=(16, 32, 48))
        self.assertTrue(output_path.endswith(".ico"))
        with Image.open(output_path) as ico:
            self.assertEqual(ico.format, "ICO")
            embedded = set(ico.ico.sizes())
        self.assertEqual(embedded, {(16, 16), (32, 32), (48, 48)})

    def test_default_sizes_when_none_given(self):
        from src.api.image_tools.image_to_ico.utils import image_to_ico

        _, output_path = image_to_ico(_png_upload())
        with Image.open(output_path) as ico:
            self.assertEqual(set(ico.ico.sizes()), {(16, 16), (32, 32), (48, 48)})
