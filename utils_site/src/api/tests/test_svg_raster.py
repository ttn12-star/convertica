"""Tests for SVG rasterization and the SVG -> ICO path."""

from __future__ import annotations

import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<rect width="64" height="64" fill="#1e90ff"/></svg>'
)


class SvgRasterTests(TestCase):
    def test_rasterizes_svg_to_png_at_target_size(self):
        from src.api.image_tools.svg_raster import rasterize_svg_to_png

        tmp = tempfile.mkdtemp()
        svg_path = os.path.join(tmp, "icon.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(_SVG)
        png_path = rasterize_svg_to_png(svg_path, tmp, target_px=128)
        with Image.open(png_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(max(img.size), 128)

    def test_svg_upload_converts_to_ico(self):
        from src.api.image_tools.image_to_ico.utils import image_to_ico

        upload = SimpleUploadedFile(
            "icon.svg", _SVG.encode("utf-8"), content_type="image/svg+xml"
        )
        _, output_path = image_to_ico(upload, sizes=(16, 32, 48))
        with Image.open(output_path) as ico:
            self.assertEqual(set(ico.ico.sizes()), {(16, 16), (32, 32), (48, 48)})
