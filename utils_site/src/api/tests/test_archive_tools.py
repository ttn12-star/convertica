from django.test import TestCase
from src.exceptions import (
    EncryptedArchiveError,
    EncryptedPDFError,
    InvalidArchiveError,
    InvalidPDFError,
)


class ArchiveExceptionsTests(TestCase):
    def test_archive_errors_subclass_pdf_errors_for_400_mapping(self):
        # base_views.handle_conversion_error maps EncryptedPDFError/InvalidPDFError to HTTP 400.
        self.assertTrue(issubclass(EncryptedArchiveError, EncryptedPDFError))
        self.assertTrue(issubclass(InvalidArchiveError, InvalidPDFError))
        self.assertEqual(str(EncryptedArchiveError("nope")), "nope")
