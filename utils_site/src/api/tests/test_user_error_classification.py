"""Conversion error classification (CONVERTICA audit Sec-1).

The task treated any exception whose message contains 'not found' as a
user-fixable error: no retry, and the raw message (incl. the internal
input_path) returned to the user. A missing INPUT file (FileNotFoundError) is
an internal/transient condition — it must retry and not leak the path.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from src.tasks.pdf_conversion import _is_user_input_error


class UserErrorClassificationTests(SimpleTestCase):
    def test_missing_input_file_is_not_a_user_error(self):
        exc = FileNotFoundError("Input file not found: /app/media/async_temp/x/in.pdf")
        self.assertFalse(_is_user_input_error(exc))

    def test_invalid_pdf_is_a_user_error(self):
        self.assertTrue(_is_user_input_error(ValueError("Invalid PDF structure")))

    def test_encrypted_is_a_user_error(self):
        self.assertTrue(
            _is_user_input_error(ValueError("This PDF is password protected"))
        )

    def test_generic_runtime_error_is_not_user_error(self):
        self.assertFalse(_is_user_input_error(RuntimeError("connection reset")))
