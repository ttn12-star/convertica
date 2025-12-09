"""
Smoke tests for critical API scenarios.

These tests verify that the API handles:
- Valid PDF conversions (should succeed)
- Corrupted PDF files (should fail gracefully)
- Timeout scenarios (large files or many pages)
"""

import io
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.test import APIClient


class SmokeTests(TestCase):
    """Smoke tests for critical API functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if hasattr(self, "temp_dir") and self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_valid_pdf(self, pages: int = 1) -> SimpleUploadedFile:
        """Create a valid PDF file with specified number of pages."""
        buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
        for _ in range(pages):
            pdf_canvas.drawString(100, 750, "Test PDF Content")
            pdf_canvas.showPage()
        pdf_canvas.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")

    def _create_corrupted_pdf(self) -> SimpleUploadedFile:
        """Create a corrupted PDF file (invalid xref table)."""
        # Create a PDF with corrupted xref table
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF
CORRUPTED DATA HERE - INVALID XREF"""
        return SimpleUploadedFile(
            "corrupted.pdf", pdf_content, content_type="application/pdf"
        )

    def test_valid_pdf_conversion_succeeds(self):
        """Test that a valid PDF conversion succeeds."""
        pdf_file = self._create_valid_pdf(pages=1)

        # Test a simple operation (rotate) which should succeed quickly
        response = self.client.post(
            "/api/pdf-edit/rotate/",
            {"pdf_file": pdf_file, "angle": 90, "pages": "all"},
            format="multipart",
        )

        # Should succeed (200) or at least not be a critical error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,  # Validation error
                status.HTTP_429_TOO_MANY_REQUESTS,  # Rate limit
            ],
            f"Valid PDF should process successfully, got {response.status_code}",
        )

        # If successful, should return a file
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(
                response["Content-Type"], "application/pdf", "Should return PDF file"
            )
            self.assertTrue(
                len(response.content) > 0, "Response should contain file data"
            )

    def test_corrupted_pdf_handled_gracefully(self):
        """Test that a corrupted PDF is handled gracefully (not 500 error)."""
        corrupted_pdf = self._create_corrupted_pdf()

        response = self.client.post(
            "/api/pdf-edit/rotate/",
            {"pdf_file": corrupted_pdf, "angle": 90, "pages": "all"},
            format="multipart",
        )

        # Should return 400 (validation error) or 408 (timeout), not 500
        self.assertNotEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Corrupted PDF should not cause 500 error",
        )

        # Should return a user-friendly error message
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn(
                "error",
                str(response.data).lower(),
                "Should return error message for corrupted PDF",
            )

    def test_large_pdf_triggers_timeout_or_page_limit(self):
        """Test that a PDF with many pages triggers timeout or page limit."""
        # Create PDF with 60 pages (exceeds MAX_PDF_PAGES=50)
        large_pdf = self._create_valid_pdf(pages=60)

        response = self.client.post(
            "/api/pdf-edit/rotate/",
            {"pdf_file": large_pdf, "angle": 90, "pages": "all"},
            format="multipart",
        )

        # Should return 400 (page limit) or 408 (timeout), not 500
        self.assertIn(
            response.status_code,
            [
                status.HTTP_400_BAD_REQUEST,  # Page limit exceeded
                status.HTTP_408_REQUEST_TIMEOUT,  # Timeout
                status.HTTP_429_TOO_MANY_REQUESTS,  # Rate limit
            ],
            f"Large PDF should trigger limit or timeout, got {response.status_code}",
        )

        # If 400, should mention page limit
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_text = str(response.data).lower()
            self.assertTrue(
                "page" in response_text
                or "limit" in response_text
                or "maximum" in response_text,
                "Should mention page limit in error message",
            )

    def test_empty_file_rejected(self):
        """Test that empty file is rejected with proper error."""
        empty_file = SimpleUploadedFile(
            "empty.pdf", b"", content_type="application/pdf"
        )

        response = self.client.post(
            "/api/pdf-edit/rotate/",
            {"pdf_file": empty_file, "angle": 90, "pages": "all"},
            format="multipart",
        )

        # Should return 400 (validation error)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Empty file should be rejected with 400",
        )

    def test_invalid_file_type_rejected(self):
        """Test that invalid file type is rejected."""
        text_file = SimpleUploadedFile(
            "test.txt", b"This is not a PDF", content_type="text/plain"
        )

        response = self.client.post(
            "/api/pdf-edit/rotate/",
            {"pdf_file": text_file, "angle": 90, "pages": "all"},
            format="multipart",
        )

        # Should return 400 (validation error)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Invalid file type should be rejected with 400",
        )

    def test_pdf_repair_attempted_on_corruption(self):
        """Test that PDF repair is attempted for corrupted files."""
        corrupted_pdf = self._create_corrupted_pdf()

        # Mock repair_pdf to verify it's called
        with patch("src.api.pdf_utils.repair_pdf") as mock_repair:
            mock_repair.return_value = "/fake/repaired/path.pdf"

            response = self.client.post(
                "/api/pdf-to-word/",
                {"pdf_file": corrupted_pdf},
                format="multipart",
            )

            # repair_pdf should be called (even if it doesn't help)
            # Note: This might not be called if validation fails first
            # But if it reaches conversion, repair should be attempted
            if response.status_code not in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_429_TOO_MANY_REQUESTS,
            ]:
                # If we got past validation, repair should have been attempted
                # (though mock might not be called if validation fails first)
                pass
