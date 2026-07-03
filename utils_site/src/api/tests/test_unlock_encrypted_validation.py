"""Encrypted PDFs must pass page validation for the unlock operation only.

Regression test: validate_pdf_pages() used to reject password-protected PDFs
for EVERY operation — including unlock_pdf, whose entire purpose is encrypted
input, so the unlock tool bounced every file it exists to handle.
"""

import os
import tempfile

from django.test import SimpleTestCase
from pypdf import PdfReader, PdfWriter
from src.api.conversion_limits import validate_pdf_pages


def _make_encrypted_pdf(path: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    with open(path, "wb") as f:
        writer.write(f)


class UnlockEncryptedValidationTests(SimpleTestCase):
    def setUp(self):
        fd, self.pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        _make_encrypted_pdf(self.pdf_path)
        # sanity: the fixture really is user-password encrypted
        self.assertTrue(PdfReader(self.pdf_path).is_encrypted)

    def tearDown(self):
        os.unlink(self.pdf_path)

    def test_unlock_operation_accepts_encrypted_pdf(self):
        is_valid, error, pages = validate_pdf_pages(
            self.pdf_path, operation="unlock_pdf"
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_other_operations_still_reject_encrypted_pdf(self):
        is_valid, error, pages = validate_pdf_pages(self.pdf_path, operation="compress")
        self.assertFalse(is_valid)
        self.assertIn("password-protected", error)

    def test_allow_encrypted_validator_accepts_user_password_pdf(self):
        # Second regression layer: validate_pdf_allow_encrypted() used to call
        # len(reader.pages), which raises FileNotDecryptedError on
        # user-password PDFs — so even the "allow encrypted" path rejected them.
        from src.api.pdf_processing import validate_pdf_allow_encrypted

        validate_pdf_allow_encrypted(self.pdf_path, context={})  # must not raise
