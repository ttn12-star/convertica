"""Tests for the `protect_image` util: images -> single AES-256 password PDF.

Covers:
* A single image produces an encrypted PDF that decrypts with the right password.
* Multiple images produce one PDF with one page per image.
* Empty/whitespace-only password is rejected.
* A non-image upload is rejected.
"""

from __future__ import annotations

import os
import shutil
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from pypdf import PdfReader
from src.api.image_tools.password_protect_image.utils import protect_image
from src.exceptions import ConversionError


def _png(color="red", size=(120, 90)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")


class ProtectImageUtilTests(TestCase):
    def test_produces_encrypted_pdf(self):
        _input_pdf, output_pdf = protect_image([_png()], password="s3cret")
        try:
            reader = PdfReader(output_pdf)
            self.assertTrue(reader.is_encrypted, "PDF must be locked")
            self.assertTrue(
                reader.decrypt("s3cret"), "correct password must open the PDF"
            )
            self.assertEqual(len(reader.pages), 1)
        finally:
            shutil.rmtree(os.path.dirname(output_pdf), ignore_errors=True)

    def test_multiple_images_one_pdf_per_page(self):
        _input_pdf, output_pdf = protect_image(
            [_png("red"), _png("blue"), _png("green")], password="pw"
        )
        try:
            reader = PdfReader(output_pdf)
            reader.decrypt("pw")
            self.assertEqual(len(reader.pages), 3)
        finally:
            shutil.rmtree(os.path.dirname(output_pdf), ignore_errors=True)

    def test_rejects_empty_password(self):
        with self.assertRaises(ConversionError):
            protect_image([_png()], password="   ")

    def test_rejects_non_image(self):
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        with self.assertRaises(ConversionError):
            protect_image([bad], password="pw")
