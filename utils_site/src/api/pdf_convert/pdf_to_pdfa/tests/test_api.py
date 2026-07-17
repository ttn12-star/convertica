"""Premium-gate tests for the PDF/A API endpoint.

The gate runs before any file processing, so these need neither Ghostscript
nor a real PDF. The conversion + encrypted-rejection logic is covered in
test_conversion.py; the 400 error mapping is base_views' shared concern.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def _payload():
    return {
        "pdf_file": SimpleUploadedFile(
            "in.pdf", b"%PDF-1.4\n", content_type="application/pdf"
        ),
        "conformance": "pdfa-2b",
    }


class PdfToPdfaPremiumGateTest(TestCase):
    def setUp(self):
        self.url = reverse("pdf_to_pdfa_api")

    def test_anonymous_gets_403(self):
        response = self.client.post(self.url, _payload())
        self.assertEqual(response.status_code, 403)

    def test_non_premium_user_gets_403(self):
        User.objects.create_user(email="free@t.test", password="pw12345!")
        self.client.login(email="free@t.test", password="pw12345!")
        response = self.client.post(self.url, _payload())
        self.assertEqual(response.status_code, 403)
