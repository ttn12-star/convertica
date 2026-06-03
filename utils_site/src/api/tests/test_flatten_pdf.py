"""Tests for the Flatten PDF endpoint and utility.

Covers:
* `flatten_pdf()` removes the interactive layer (widgets + annotations).
* Filled-in form values are PRESERVED in the static content — the tool
  promises the flattened PDF "looks identical", so baking the appearance
  (not deleting it) is the contract. This guards the regression where
  `delete_widget()` silently dropped user-entered values.
* The API view processes a real request and returns a PDF blob.
"""

from __future__ import annotations

import fitz  # PyMuPDF
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from src.api.pdf_edit.flatten_pdf.utils import flatten_pdf


def _make_filled_form_pdf() -> bytes:
    """A one-page PDF with a filled text field and a checked checkbox."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Form below:")

    text_widget = fitz.Widget()
    text_widget.field_name = "name"
    text_widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    text_widget.rect = fitz.Rect(72, 100, 300, 120)
    text_widget.field_value = "FILLED VALUE"
    page.add_widget(text_widget)

    checkbox = fitz.Widget()
    checkbox.field_name = "agree"
    checkbox.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    checkbox.rect = fitz.Rect(72, 130, 90, 148)
    checkbox.field_value = True
    page.add_widget(checkbox)

    out = doc.write()
    doc.close()
    return out


def _make_annotated_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Text with a highlight and a note.")
    page.add_highlight_annot(fitz.Rect(72, 66, 200, 78))
    page.add_text_annot((300, 100), "a sticky note")
    out = doc.write()
    doc.close()
    return out


class FlattenPDFUtilTests(TestCase):
    def test_removes_interactive_layer(self):
        upload = SimpleUploadedFile(
            "form.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        _input_path, output_path = flatten_pdf(upload)

        doc = fitz.open(output_path)
        page = doc[0]
        self.assertEqual(len(list(page.widgets())), 0, "widgets must be removed")
        self.assertEqual(len(list(page.annots())), 0, "annotations must be removed")
        doc.close()

    def test_preserves_filled_form_value(self):
        """The flattened PDF must keep the value the user typed into the form."""
        upload = SimpleUploadedFile(
            "form.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        _input_path, output_path = flatten_pdf(upload)

        doc = fitz.open(output_path)
        text = doc[0].get_text()
        doc.close()
        self.assertIn(
            "FILLED VALUE",
            text,
            "filled form value was lost during flattening",
        )

    def test_annotation_appearance_is_baked(self):
        upload = SimpleUploadedFile(
            "annot.pdf", _make_annotated_pdf(), content_type="application/pdf"
        )
        _input_path, output_path = flatten_pdf(upload)

        doc = fitz.open(output_path)
        page = doc[0]
        # The interactive annotation objects are gone …
        self.assertEqual(len(list(page.annots())), 0)
        # … but the underlying text content survives.
        self.assertIn("Text with a highlight", page.get_text())
        doc.close()


class FlattenPDFAPITests(TestCase):
    def test_endpoint_returns_pdf(self):
        client = Client()
        upload = SimpleUploadedFile(
            "form.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        resp = client.post(
            "/api/pdf-edit/flatten/",
            {"pdf_file": upload},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        body = b"".join(resp.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
