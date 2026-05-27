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
