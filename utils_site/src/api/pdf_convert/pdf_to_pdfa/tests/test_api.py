"""Premium-gate tests for the PDF/A API endpoint.

The gate runs before any file processing, so these need neither Ghostscript
nor a real PDF. The conversion + encrypted-rejection logic is covered in
test_conversion.py; the 400 error mapping is base_views' shared concern.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class PdfToPdfaHeavyTierTest(TestCase):
    """PDF/A must be in the heavy tier — that's what gets it the 300s timeout
    and the stricter *free* caps; gs is slow on scans. Premium gets the full
    advertised caps here, same as the light tier."""

    def test_classified_heavy(self):
        from src.api.conversion_limits import (
            HEAVY_OPERATIONS,
            MAX_FILE_SIZE_HEAVY_PREMIUM,
            MAX_PDF_PAGES_HEAVY_PREMIUM,
            get_max_file_size_for_user,
            get_max_pages_for_user,
        )

        self.assertIn("pdf_to_pdfa", HEAVY_OPERATIONS)

        premium = User.objects.create_user(email="pro2@t.test", password="pw12345!")
        premium.is_premium = True
        premium.subscription_start_date = timezone.now() - timedelta(days=1)
        premium.subscription_end_date = timezone.now() + timedelta(days=30)
        premium._skip_days_calculation = True
        premium.save()

        # Premium resolves through the heavy-tier constants.
        self.assertEqual(
            get_max_pages_for_user(premium, "pdf_to_pdfa"), MAX_PDF_PAGES_HEAVY_PREMIUM
        )
        self.assertEqual(
            get_max_file_size_for_user(premium, "pdf_to_pdfa"),
            MAX_FILE_SIZE_HEAVY_PREMIUM,
        )


class PdfToPdfaAsyncGateTest(TestCase):
    """The async endpoint must be premium-gated too (parity with sync)."""

    def test_async_anonymous_gets_403(self):
        resp = self.client.post(reverse("pdf_to_pdfa_async_api"), _payload())
        self.assertEqual(resp.status_code, 403)

    def test_async_non_premium_gets_403(self):
        User.objects.create_user(email="free3@t.test", password="pw12345!")
        self.client.login(email="free3@t.test", password="pw12345!")
        resp = self.client.post(reverse("pdf_to_pdfa_async_api"), _payload())
        self.assertEqual(resp.status_code, 403)
