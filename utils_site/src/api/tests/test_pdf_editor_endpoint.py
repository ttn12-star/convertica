"""Tests for the PdfEditorAPIView endpoint.

The PDF Editor endpoint reuses AddTextPDFSerializer + add_text_pdf() under
a distinct CONVERSION_TYPE ("pdf_editor") so the head-cluster /pdf-editor/
page gets its own OperationRun metrics without a duplicate backend. Free,
no batch — modeled on SignPDFViewTests in test_sign_pdf.py.
"""

from __future__ import annotations

import json

import fitz  # PyMuPDF
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings


def _make_pdf_bytes(pages: int = 1) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=612, height=792)
    out = doc.write()
    doc.close()
    return out


@override_settings(RATELIMIT_ENABLE=False)
class PdfEditorEndpointTests(TestCase):
    """Happy path through the real view — a shape op is enough (no image)."""

    URL = "/api/pdf-edit/editor/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        # Browser-shaped Referer satisfies CaptchaRequirementMiddleware so the
        # spam-protection gate doesn't reject test requests with 400 captcha_required.
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"
        self.operations_json = json.dumps(
            [
                {
                    "type": "shape",
                    "page": 0,
                    "x": 10,
                    "y": 10,
                    "width": 80,
                    "height": 40,
                    "shape_kind": "rect",
                    "stroke": "#ff0000",
                }
            ]
        )

    def _post(self):
        pdf = SimpleUploadedFile(
            "input.pdf", _make_pdf_bytes(), content_type="application/pdf"
        )
        return self.client.post(
            self.URL,
            data={"pdf_file": pdf, "operations": self.operations_json},
            format="multipart",
        )

    def test_endpoint_returns_pdf(self):
        response = self._post()
        body = b"".join(response.streaming_content)
        self.assertEqual(response.status_code, 200, body[:300])
        self.assertEqual(response["Content-Type"], "application/pdf")
