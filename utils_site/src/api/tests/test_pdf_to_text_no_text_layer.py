"""A scanned (image-only) PDF must fail as bad input, not as a 500.

Guards the empty-extraction branch in convert_pdf_to_text: before the fix, a PDF
with no text layer wrote a 0-byte .txt, tripped validate_output_file and raised a
plain ConversionError, which the API layer logs at exception level and answers
with HTTP 500 (Sentry CONVERTICA-5J).
"""

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_convert.pdf_to_text.utils import convert_pdf_to_text
from src.exceptions import InvalidPDFError


def _pdf_without_text_layer() -> bytes:
    """One blank page: no text to extract, but a structurally valid PDF."""
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


class PdfToTextNoTextLayerTests(SimpleTestCase):
    def test_no_text_layer_raises_invalid_pdf_error(self):
        upload = SimpleUploadedFile(
            "scan.pdf", _pdf_without_text_layer(), content_type="application/pdf"
        )

        with self.assertRaises(InvalidPDFError) as caught:
            convert_pdf_to_text(upload)

        # InvalidPDFError is what base_views maps to HTTP 400 + a warning log.
        self.assertIn("no text layer", str(caught.exception))

    def test_pdf_with_text_still_converts(self):
        doc = fitz.open()
        doc.new_page().insert_text((72, 72), "hello convertica")
        data = doc.tobytes()
        doc.close()

        _input_path, output_path = convert_pdf_to_text(
            SimpleUploadedFile("doc.pdf", data, content_type="application/pdf")
        )

        with open(output_path, encoding="utf-8") as file_obj:
            self.assertIn("hello convertica", file_obj.read())
