"""Tests for the new coordinate-based Sign PDF endpoint.

Covers:
* Serializer accepts/rejects the JSON `signatures` payload shape.
* `sign_pdf()` utility actually embeds the image at the requested
  coordinates and produces a valid PDF.
* The API view gates non-premium users with a clear error.
* The API view processes a real signed request and returns a PDF blob.
"""

from __future__ import annotations

import base64
import io
import json
from datetime import timedelta

import fitz  # PyMuPDF
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image, ImageDraw
from src.api.pdf_edit.sign_pdf.serializers import SignPDFSerializer
from src.api.pdf_edit.sign_pdf.utils import sign_pdf
from src.users.models import User


def _make_pdf_bytes(pages: int = 1) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=612, height=792)
    out = doc.write()
    doc.close()
    return out


def _make_signature_data_uri() -> str:
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    ImageDraw.Draw(img).line([(5, 25), (55, 5), (55, 25)], fill=(0, 0, 0, 255), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class SignPDFSerializerTests(TestCase):
    """Serializer-level rejections for the JSON `signatures` array."""

    def setUp(self):
        self.pdf = SimpleUploadedFile(
            "test.pdf", _make_pdf_bytes(), content_type="application/pdf"
        )
        self.sig_uri = _make_signature_data_uri()

    def _ok_payload(self) -> dict:
        return {
            "pdf_file": self.pdf,
            "signatures": json.dumps(
                [
                    {
                        "page": 0,
                        "x": 100,
                        "y": 700,
                        "width": 150,
                        "height": 60,
                        "image_data_uri": self.sig_uri,
                    }
                ]
            ),
        }

    def test_valid_payload_parses(self):
        s = SignPDFSerializer(data=self._ok_payload())
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(len(s.validated_data["signatures"]), 1)
        self.assertEqual(s.validated_data["signatures"][0]["page"], 0)

    def test_missing_signatures_rejected(self):
        s = SignPDFSerializer(data={"pdf_file": self.pdf})
        self.assertFalse(s.is_valid())
        self.assertIn("signatures", s.errors)

    def test_empty_signatures_array_rejected(self):
        s = SignPDFSerializer(data={"pdf_file": self.pdf, "signatures": "[]"})
        self.assertFalse(s.is_valid())
        self.assertIn("signatures", s.errors)

    def test_malformed_json_rejected(self):
        s = SignPDFSerializer(data={"pdf_file": self.pdf, "signatures": "{not-json"})
        self.assertFalse(s.is_valid())

    def test_non_data_uri_image_rejected(self):
        bad = json.dumps(
            [
                {
                    "page": 0,
                    "x": 1,
                    "y": 1,
                    "width": 100,
                    "height": 50,
                    "image_data_uri": "http://evil.example/img.png",
                }
            ]
        )
        s = SignPDFSerializer(data={"pdf_file": self.pdf, "signatures": bad})
        self.assertFalse(s.is_valid())

    def test_too_many_signatures_rejected(self):
        items = [
            {
                "page": 0,
                "x": i * 5,
                "y": i * 5,
                "width": 50,
                "height": 30,
                "image_data_uri": self.sig_uri,
            }
            for i in range(SignPDFSerializer.MAX_SIGNATURES + 1)
        ]
        s = SignPDFSerializer(
            data={"pdf_file": self.pdf, "signatures": json.dumps(items)}
        )
        self.assertFalse(s.is_valid())


class SignPDFUtilTests(TestCase):
    """`sign_pdf()` actually inserts an image at the requested rect."""

    def setUp(self):
        self.sig_uri = _make_signature_data_uri()

    def _upload(self, pages: int = 1) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            "doc.pdf", _make_pdf_bytes(pages), content_type="application/pdf"
        )

    def test_single_signature_embeds_image(self):
        _, output = sign_pdf(
            self._upload(),
            signatures=[
                {
                    "page": 0,
                    "x": 200,
                    "y": 700,
                    "width": 150,
                    "height": 60,
                    "image_data_uri": self.sig_uri,
                }
            ],
        )
        doc = fitz.open(output)
        try:
            self.assertEqual(len(doc), 1)
            self.assertEqual(len(doc[0].get_images(full=True)), 1)
        finally:
            doc.close()

    def test_multiple_signatures_across_pages(self):
        _, output = sign_pdf(
            self._upload(pages=3),
            signatures=[
                {
                    "page": 0,
                    "x": 50,
                    "y": 50,
                    "width": 100,
                    "height": 40,
                    "image_data_uri": self.sig_uri,
                },
                {
                    "page": 2,
                    "x": 200,
                    "y": 700,
                    "width": 100,
                    "height": 40,
                    "image_data_uri": self.sig_uri,
                },
            ],
        )
        doc = fitz.open(output)
        try:
            self.assertEqual(len(doc[0].get_images(full=True)), 1)
            self.assertEqual(len(doc[1].get_images(full=True)), 0)
            self.assertEqual(len(doc[2].get_images(full=True)), 1)
        finally:
            doc.close()


@override_settings(PAYMENTS_ENABLED=True, RATELIMIT_ENABLE=False)
class SignPDFViewTests(TestCase):
    """Premium gate + happy path through the real view."""

    URL = "/api/pdf-edit/sign/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(email="sign@t.test", password="passw0rd!")
        self.sig_uri = _make_signature_data_uri()
        self.signatures_json = json.dumps(
            [
                {
                    "page": 0,
                    "x": 200,
                    "y": 700,
                    "width": 150,
                    "height": 60,
                    "image_data_uri": self.sig_uri,
                }
            ]
        )

    def _post(self):
        pdf = SimpleUploadedFile(
            "input.pdf", _make_pdf_bytes(), content_type="application/pdf"
        )
        return self.client.post(
            self.URL,
            data={"pdf_file": pdf, "signatures": self.signatures_json},
            format="multipart",
        )

    def test_anonymous_blocked(self):
        response = self._post()
        self.assertEqual(response.status_code, 403)

    def test_authenticated_free_user_blocked(self):
        self.client.force_login(self.user)
        response = self._post()
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertIn("premium", body.get("error", "").lower())

    def test_premium_user_signs_successfully(self):
        self.user.is_premium = True
        self.user.subscription_start_date = timezone.now() - timedelta(days=1)
        self.user.subscription_end_date = timezone.now() + timedelta(days=30)
        self.user._admin_manual_edit = True
        self.user.save()

        self.client.force_login(self.user)
        response = self._post()
        # FileResponse is streaming — consume the chunks.
        body = b"".join(response.streaming_content)
        self.assertEqual(response.status_code, 200, body[:300])
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(body), 1000)
        # The returned bytes must parse as a valid PDF with the embedded signature.
        doc = fitz.open(stream=body, filetype="pdf")
        try:
            self.assertEqual(len(doc), 1)
            self.assertEqual(len(doc[0].get_images(full=True)), 1)
        finally:
            doc.close()
