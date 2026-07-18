"""Round-2 input-hardening regressions: watermark image + signature data-URI
must be validated (size + real type) before reaching PIL/fitz."""

import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_edit.add_watermark.serializers import AddWatermarkSerializer
from src.api.pdf_edit.sign_pdf.serializers import SignatureItemSerializer

_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class WatermarkFileValidationTests(SimpleTestCase):
    def _field_errs(self, upload):
        s = AddWatermarkSerializer(
            data={
                "pdf_file": SimpleUploadedFile("d.pdf", b"%PDF-1.4"),
                "watermark_file": upload,
            }
        )
        s.is_valid()
        return s.errors

    def test_real_png_watermark_accepted(self):
        up = SimpleUploadedFile("wm.png", _PNG_1PX, content_type="image/png")
        self.assertNotIn("watermark_file", self._field_errs(up))

    def test_non_image_watermark_rejected(self):
        up = SimpleUploadedFile(
            "wm.png", b"not an image at all", content_type="image/png"
        )
        self.assertIn("watermark_file", self._field_errs(up))


class SignatureDataUriTests(SimpleTestCase):
    def _errs(self, uri):
        s = SignatureItemSerializer(
            data={
                "page": 0,
                "x": 1,
                "y": 1,
                "width": 50,
                "height": 50,
                "image_data_uri": uri,
            }
        )
        s.is_valid()
        return s.errors

    def test_png_data_uri_accepted(self):
        uri = "data:image/png;base64," + base64.b64encode(_PNG_1PX).decode()
        self.assertNotIn("image_data_uri", self._errs(uri))

    def test_disallowed_subtype_rejected(self):
        uri = "data:image/gif;base64," + base64.b64encode(_PNG_1PX).decode()
        self.assertIn("image_data_uri", self._errs(uri))

    def test_oversized_decoded_rejected(self):
        big = base64.b64encode(b"\x00" * (3 * 1024 * 1024 + 10)).decode()
        uri = "data:image/png;base64," + big
        self.assertIn("image_data_uri", self._errs(uri))
