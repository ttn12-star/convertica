"""Conformance tests for the PDF/A converter.

The happy-path cases need Ghostscript on the host; they self-skip when absent
(full check runs in the container). The encrypted-input rejection needs no gs.
"""

import re
import shutil
import unittest

import fitz  # PyMuPDF — synthesises fixtures and inspects the output
from django.core.files.uploadedfile import SimpleUploadedFile
from src.api.pdf_convert.pdf_to_pdfa.utils import convert_pdf_to_pdfa
from src.exceptions import EncryptedPDFError


def _pdfa_part(path: str) -> str:
    doc = fitz.open(path)
    try:
        oi_type, oi_value = doc.xref_get_key(doc.pdf_catalog(), "OutputIntents")
        has_intent = oi_type != "null" and bool(oi_value)
        match = re.search(r"pdfaid:part[^0-9]{0,8}(\d+)", doc.get_xml_metadata() or "")
        return "%s:%s" % (has_intent, match.group(1) if match else "")
    finally:
        doc.close()


def _one_page_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Convertica PDF/A test")
    data = doc.tobytes()
    doc.close()
    return data


def _upload(data: bytes, name: str = "in.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data, content_type="application/pdf")


@unittest.skipUnless(shutil.which("gs"), "Ghostscript not installed on host")
class PdfToPdfaConversionTest(unittest.TestCase):
    def test_produces_conformant_pdfa_2b(self):
        _, out = convert_pdf_to_pdfa(_upload(_one_page_pdf()), conformance="pdfa-2b")
        self.assertEqual(_pdfa_part(out), "True:2")

    def test_level_1b_declares_part_1(self):
        _, out = convert_pdf_to_pdfa(_upload(_one_page_pdf()), conformance="pdfa-1b")
        self.assertEqual(_pdfa_part(out), "True:1")


class PdfToPdfaRejectionTest(unittest.TestCase):
    def test_encrypted_input_rejected(self):
        doc = fitz.open()
        doc.new_page()
        enc = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="x", user_pw="x"
        )
        doc.close()
        with self.assertRaises(EncryptedPDFError):
            convert_pdf_to_pdfa(_upload(enc, "enc.pdf"), conformance="pdfa-2b")
