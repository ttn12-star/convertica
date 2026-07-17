"""Tests for the Add Text to PDF tool.

Covers serializer validation, end-to-end materialization (the added text
comes back as real, extractable text; whiteout/highlight draw vectors),
Unicode shaping, and the .po i18n contract (content-based, since CI does
not run compilemessages — see memory feedback_ci_no_compilemessages).
"""

import io
from pathlib import Path

import fitz
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_edit.add_text.serializers import AddTextPDFSerializer
from src.api.pdf_edit.add_text.utils import add_text_pdf


def _pdf_bytes(width=595, height=842, pages=1):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=width, height=height)
    data = doc.tobytes()
    doc.close()
    return data


def _upload(data=None):
    return SimpleUploadedFile(
        "sample.pdf", data or _pdf_bytes(), content_type="application/pdf"
    )


class AddTextSerializerTests(SimpleTestCase):
    def _validate(self, operations_json):
        s = AddTextPDFSerializer(
            data={"pdf_file": _upload(), "operations": operations_json}
        )
        return s

    def test_valid_text_operation(self):
        s = self._validate(
            '[{"type":"text","page":0,"x":50,"y":50,"width":200,"height":40,'
            '"text":"Hello","font_size":14,"color":"#111111"}]'
        )
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(len(s.validated_data["operations"]), 1)

    def test_empty_operations_rejected(self):
        self.assertFalse(self._validate("[]").is_valid())

    def test_malformed_json_rejected(self):
        self.assertFalse(self._validate("not json").is_valid())

    def test_bad_color_rejected(self):
        s = self._validate(
            '[{"type":"text","page":0,"x":1,"y":1,"width":50,"height":20,'
            '"text":"x","color":"red"}]'
        )
        self.assertFalse(s.is_valid())

    def test_blank_text_rejected(self):
        s = self._validate(
            '[{"type":"text","page":0,"x":1,"y":1,"width":50,"height":20,"text":"   "}]'
        )
        self.assertFalse(s.is_valid())

    def test_too_many_operations_rejected(self):
        items = ",".join(
            '{"type":"whiteout","page":0,"x":1,"y":1,"width":10,"height":10}'
            for _ in range(AddTextPDFSerializer.MAX_OPERATIONS + 1)
        )
        self.assertFalse(self._validate(f"[{items}]").is_valid())

    def test_whiteout_needs_no_text(self):
        s = self._validate(
            '[{"type":"whiteout","page":0,"x":10,"y":10,"width":50,"height":20}]'
        )
        self.assertTrue(s.is_valid(), s.errors)


class AddTextMaterializationTests(SimpleTestCase):
    def _run(self, operations):
        _in, out = add_text_pdf(_upload(), operations=operations)
        return fitz.open(out)

    def test_text_is_real_extractable_text(self):
        doc = self._run(
            [
                {
                    "type": "text",
                    "page": 0,
                    "x": 60,
                    "y": 60,
                    "width": 300,
                    "height": 40,
                    "text": "Convertica Add Text",
                    "font_key": "sans",
                    "font_size": 16,
                    "color": "#111111",
                }
            ]
        )
        self.assertIn("Convertica Add Text", doc[0].get_text())

    def test_cyrillic_text_preserved(self):
        doc = self._run(
            [
                {
                    "type": "text",
                    "page": 0,
                    "x": 60,
                    "y": 60,
                    "width": 300,
                    "height": 40,
                    "text": "Привет мир",
                    "font_key": "sans",
                    "font_size": 16,
                    "color": "#111111",
                }
            ]
        )
        self.assertIn("Привет", doc[0].get_text())

    def test_whiteout_and_highlight_draw_vectors(self):
        doc = self._run(
            [
                {
                    "type": "whiteout",
                    "page": 0,
                    "x": 40,
                    "y": 40,
                    "width": 100,
                    "height": 20,
                    "color": "#ffffff",
                },
                {
                    "type": "highlight",
                    "page": 0,
                    "x": 40,
                    "y": 80,
                    "width": 120,
                    "height": 18,
                    "color": "#ffee00",
                },
            ]
        )
        self.assertGreaterEqual(len(doc[0].get_drawings()), 2)

    def test_page_index_clamped(self):
        # page 99 on a 1-page doc must not raise; it clamps to the last page.
        doc = self._run(
            [
                {
                    "type": "text",
                    "page": 99,
                    "x": 10,
                    "y": 10,
                    "width": 100,
                    "height": 30,
                    "text": "clamp",
                    "font_size": 12,
                    "color": "#000000",
                }
            ]
        )
        self.assertEqual(len(doc), 1)


class AddTextI18nTests(SimpleTestCase):
    LOCALES = ("ar", "en", "es", "hi", "id", "pl", "ru")
    MARKERS = (
        "Add Text to PDF",
        "Whiteout & Highlight",
        "Will the added text stay selectable in the PDF?",
    )

    def test_markers_present_in_every_locale(self):
        base = Path(settings.BASE_DIR) / "locale"
        for lang in self.LOCALES:
            po = (base / lang / "LC_MESSAGES" / "django.po").read_text("utf-8")
            for marker in self.MARKERS:
                self.assertIn(
                    'msgid "%s"' % marker, po, f"{lang}: missing msgid {marker!r}"
                )
