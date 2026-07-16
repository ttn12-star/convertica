"""Regression: the Celery path of jpg_to_pdf must produce a real PDF.

generic_conversion_task calls the public convert_jpg_to_pdf with
is_celery_task=True. Until 2026-07 optimization_manager routed that branch
back through the same public function, re-entering itself with the flag
still in kwargs — TypeError (duplicated ``suffix``) on every async request.
"""

from __future__ import annotations

import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image


class JpgToPdfCeleryPathTests(SimpleTestCase):
    def test_celery_kwargs_produce_valid_pdf(self):
        import asyncio

        from src.api.pdf_convert.jpg_to_pdf.utils import convert_jpg_to_pdf

        buf = io.BytesIO()
        Image.new("RGB", (40, 40), (200, 30, 30)).save(buf, "JPEG")
        upload = SimpleUploadedFile("photo.jpg", buf.getvalue(), "image/jpeg")

        _, pdf_path = asyncio.run(
            convert_jpg_to_pdf(
                upload,
                suffix="_convertica",
                is_celery_task=True,
                context={},
                check_cancelled=lambda: None,
            )
        )

        self.assertTrue(os.path.exists(pdf_path))
        with open(pdf_path, "rb") as fh:
            self.assertEqual(fh.read(5), b"%PDF-")
