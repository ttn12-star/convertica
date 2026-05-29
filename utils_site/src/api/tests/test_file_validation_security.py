"""Security-branch coverage for file_validation (CONVERTICA audit).

validate_word_file / validate_pdf_file are the primary defense in front of
LibreOffice/unoserver and PyPDF (macro-RCE, crafted-OOXML CVEs, memory DoS).
They had effectively zero direct test coverage. These pin the reject/accept
behavior so a regression that loosens validation is caught.
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile

from django.test import SimpleTestCase
from src.api.file_validation import (
    encode_filename_for_header,
    validate_pdf_file,
    validate_word_file,
)


def _tmp(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _valid_docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<document/>")
    return buf.getvalue()


def _valid_pdf_bytes(encrypted: bool = False) -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    if encrypted:
        w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


class ValidateWordFileTests(SimpleTestCase):
    def test_macro_enabled_docm_rejected(self):
        ok, msg = validate_word_file(_tmp(_valid_docx_bytes(), ".docm"), {})
        self.assertFalse(ok)
        self.assertIn("macro", msg.lower())

    def test_missing_magic_bytes_rejected(self):
        ok, msg = validate_word_file(_tmp(b"not an office file at all", ".docx"), {})
        self.assertFalse(ok)

    def test_docx_missing_required_parts_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("random.txt", "x")  # PK header but not a real OOXML pkg
        ok, msg = validate_word_file(_tmp(buf.getvalue(), ".docx"), {})
        self.assertFalse(ok)

    def test_valid_docx_accepted(self):
        ok, msg = validate_word_file(_tmp(_valid_docx_bytes(), ".docx"), {})
        self.assertTrue(ok, msg)


class ValidatePdfFileTests(SimpleTestCase):
    def test_empty_rejected(self):
        ok, _ = validate_pdf_file(_tmp(b"", ".pdf"), {})
        self.assertFalse(ok)

    def test_too_small_rejected(self):
        ok, _ = validate_pdf_file(_tmp(b"%PDF-1.4", ".pdf"), {})
        self.assertFalse(ok)

    def test_missing_pdf_header_rejected(self):
        ok, _ = validate_pdf_file(_tmp(b"X" * 500, ".pdf"), {})
        self.assertFalse(ok)

    def test_encrypted_pdf_rejected(self):
        ok, msg = validate_pdf_file(_tmp(_valid_pdf_bytes(encrypted=True), ".pdf"), {})
        self.assertFalse(ok)
        self.assertIn("password", msg.lower())

    def test_valid_pdf_accepted(self):
        ok, msg = validate_pdf_file(_tmp(_valid_pdf_bytes(), ".pdf"), {})
        self.assertTrue(ok, msg)


class EncodeFilenameForHeaderTests(SimpleTestCase):
    def test_ascii_filename(self):
        self.assertEqual(
            encode_filename_for_header("document.pdf"),
            'attachment; filename="document.pdf"',
        )

    def test_cyrillic_filename_uses_rfc5987(self):
        out = encode_filename_for_header("документ.pdf")
        self.assertIn("filename*=UTF-8''", out)
        self.assertIn('filename="file.pdf"', out)
