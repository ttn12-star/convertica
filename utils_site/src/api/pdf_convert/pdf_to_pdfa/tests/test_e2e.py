"""End-to-end: a premium user drives the real view stack to a PDF/A download.

Exercises URL → middleware → premium gate → serializer → perform_conversion →
Ghostscript → conformance verify → streaming response, then validates that the
downloaded bytes are actually PDF/A. Needs gs (self-skips without it).
"""

import io
import re
import shutil
import unittest
from datetime import timedelta

import fitz
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from src.users.models import User


def _real_pdf(pages: int = 3) -> SimpleUploadedFile:
    doc = fitz.open()
    for i in range(pages):
        p = doc.new_page()
        p.insert_text((72, 72), f"Convertica PDF/A e2e — page {i + 1}")
    data = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("in.pdf", data, content_type="application/pdf")


@override_settings(PAYMENTS_ENABLED=True, RATELIMIT_ENABLE=False)
@unittest.skipUnless(shutil.which("gs"), "Ghostscript not installed on host")
class PdfToPdfaE2ETest(TestCase):
    def setUp(self):
        cache.clear()  # drop stale user_premium_active:{pk} keys
        self.client = Client()
        self.user = User.objects.create_user(email="pro@t.test", password="passw0rd!")
        self.user.is_premium = True
        self.user.subscription_start_date = timezone.now() - timedelta(days=1)
        self.user.subscription_end_date = timezone.now() + timedelta(days=30)
        self.user._skip_days_calculation = True
        self.user.save()
        self.client.force_login(self.user)

    def test_premium_user_downloads_valid_pdfa(self):
        response = self.client.post(
            "/api/pdf-to-pdfa/",
            data={"pdf_file": _real_pdf(), "conformance": "pdfa-2b"},
            format="multipart",
        )
        self.assertEqual(
            response.status_code, 200, getattr(response, "content", b"")[:300]
        )
        self.assertEqual(response["Content-Type"], "application/pdf")

        body = (
            b"".join(response.streaming_content)
            if response.streaming
            else response.content
        )
        doc = fitz.open(stream=body, filetype="pdf")
        try:
            oi_type, oi_value = doc.xref_get_key(doc.pdf_catalog(), "OutputIntents")
            self.assertEqual(oi_type, "array")
            self.assertTrue(oi_value)
            part = re.search(
                r"pdfaid:part[^0-9]{0,8}(\d+)", doc.get_xml_metadata() or ""
            )
            self.assertIsNotNone(part)
            self.assertEqual(part.group(1), "2")
        finally:
            doc.close()
