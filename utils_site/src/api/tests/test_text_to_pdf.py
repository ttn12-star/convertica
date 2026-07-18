"""Tests for the Text to PDF endpoint.

Covers the two pieces of non-trivial logic:
* build_html — HTML-escaping (injection guard) + style option mapping.
* TextToPDFSerializer — empty rejection, per-tier char limit, enum/color validation.

The view test drives the full HTTP path (middleware, serializer, response
streaming) with the Playwright render mocked out, so it runs in CI where no
Chromium is installed. The real render is verified separately (convert_text_to_pdf).
"""

from __future__ import annotations

import tempfile
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from src.api.text_convert.serializers import TextToPDFSerializer
from src.api.text_convert.utils import build_html


class BuildHTMLTests(TestCase):
    def test_escapes_markup(self):
        html = build_html("a < b & <script>x</script>")
        self.assertIn("&lt; b &amp; &lt;script&gt;", html)
        self.assertNotIn("<script>x", html)

    def test_applies_style_options(self):
        html = build_html(
            "hi", font="mono", font_size=20, color="#ff0000", align="center"
        )
        self.assertIn("20pt", html)
        self.assertIn("#ff0000", html)
        self.assertIn("text-align:center", html)
        self.assertIn("monospace", html)
        self.assertIn("pre-wrap", html)  # newlines/spacing preserved

    def test_bad_align_falls_back_to_left(self):
        html = build_html("hi", align="'; DROP TABLE")
        self.assertIn("text-align:left", html)
        self.assertNotIn("DROP TABLE", html)


class TextToPDFSerializerTests(TestCase):
    def test_empty_text_rejected(self):
        s = TextToPDFSerializer(data={"text": "   "})
        self.assertFalse(s.is_valid())
        self.assertIn("text", s.errors)

    def test_valid_defaults(self):
        s = TextToPDFSerializer(data={"text": "hello"})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["font"], "sans")
        self.assertEqual(s.validated_data["page_size"], "A4")

    def test_bad_color_rejected(self):
        s = TextToPDFSerializer(data={"text": "x", "color": "red"})
        self.assertFalse(s.is_valid())
        self.assertIn("color", s.errors)

    def test_font_size_out_of_range_rejected(self):
        s = TextToPDFSerializer(data={"text": "x", "font_size": 200})
        self.assertFalse(s.is_valid())
        self.assertIn("font_size", s.errors)

    def test_bad_page_size_rejected(self):
        s = TextToPDFSerializer(data={"text": "x", "page_size": "A0"})
        self.assertFalse(s.is_valid())

    @override_settings(TEXT_TO_PDF_MAX_CHARS_FREE=10, TEXT_TO_PDF_MAX_CHARS_PREMIUM=100)
    def test_char_limit_enforced_for_anonymous(self):
        s = TextToPDFSerializer(data={"text": "x" * 11}, context={"request": None})
        self.assertFalse(s.is_valid())
        self.assertIn("text", s.errors)

    @override_settings(TEXT_TO_PDF_MAX_CHARS_FREE=10, TEXT_TO_PDF_MAX_CHARS_PREMIUM=100)
    def test_under_limit_ok(self):
        s = TextToPDFSerializer(data={"text": "x" * 9})
        self.assertTrue(s.is_valid(), s.errors)


class TextToPDFViewTests(TestCase):
    """Full HTTP path: anonymous request renders a real PDF (free tool)."""

    URL = "/api/text-to-pdf/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        # Browser-shaped Referer satisfies the anti-spam captcha gate in tests.
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    def _fake_render(self, *_args, **_kwargs):
        """Stand-in for the Playwright render: write a minimal real PDF."""
        d = tempfile.mkdtemp(prefix="t2p_test_")
        pdf = f"{d}/document_convertica.pdf"
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%%EOF\n")
        return f"{d}/document.html", pdf

    def test_anonymous_creates_pdf(self):
        # Mock the browser render (no Chromium in CI); still exercises the full
        # HTTP path: captcha gate, quota middleware, serializer, file streaming.
        with mock.patch(
            "src.api.text_convert.views.convert_text_to_pdf",
            side_effect=self._fake_render,
        ) as m:
            response = self.client.post(
                self.URL,
                data={
                    "text": "Hello world.\nこんにちは\nمرحبا",
                    "font": "serif",
                    "font_size": 16,
                    "color": "#0a0a0a",
                    "align": "center",
                    "page_size": "A4",
                    "margin": "normal",
                },
            )
        body = b"".join(response.streaming_content)
        self.assertEqual(response.status_code, 200, body[:300])
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(body.startswith(b"%PDF"), body[:20])
        # The view forwarded the validated style options to the renderer.
        self.assertTrue(m.called)
        _, kwargs = m.call_args
        self.assertEqual(kwargs.get("font"), "serif")
        self.assertEqual(kwargs.get("align"), "center")

    def test_empty_text_rejected_by_view(self):
        response = self.client.post(self.URL, data={"text": "   "})
        self.assertEqual(response.status_code, 400)
