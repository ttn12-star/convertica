"""Tests for the PDF page-size (re-sheet) utility.

The contract that matters is geometric, so the assertions are geometric:

* the output really is the requested paper size;
* ``auto`` keeps content at 100% when it fits, so a printable stays physically
  exact and does not quietly become 94% of itself;
* ``auto`` never loses content, which is the whole reason the mode exists. A4
  is 17.6 mm taller than Letter, so a tight-margin or full-bleed page has to
  shrink instead of being cropped;
* every page of a document gets the SAME scale, or a multi-page planner prints
  with its grid drifting between sheets.
"""

from __future__ import annotations

import re

import fitz
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from src.api.pdf_edit.resize_pdf.utils import MM, PAGE_SIZES, _content_bbox, resize_pdf
from src.exceptions import InvalidPDFError

A4 = PAGE_SIZES["a4"]
LETTER = PAGE_SIZES["letter"]
LEGAL = PAGE_SIZES["legal"]


def _make_pdf(size=A4, margin_mm=12.0, pages=1, full_bleed=False) -> bytes:
    """A PDF whose ink sits a known distance from the page edge."""
    doc = fitz.open()
    width, height = size
    for number in range(pages):
        page = doc.new_page(width=width, height=height)
        if full_bleed:
            page.draw_rect(fitz.Rect(0, 0, width, height), fill=(0.9, 0.5, 0.2))
        margin = margin_mm * MM
        page.draw_rect(
            fitz.Rect(margin, margin, width - margin, height - margin),
            color=(0, 0, 0),
            width=1.2,
        )
        page.insert_text((margin + 10, margin + 24), f"page {number + 1}", fontsize=12)
    out = doc.write()
    doc.close()
    return out


def _upload(data: bytes, name: str = "printable.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data, content_type="application/pdf")


def _convert(data: bytes, **kwargs) -> fitz.Document:
    _, output_path = resize_pdf(_upload(data), **kwargs)
    return fitz.open(output_path)


def _ink_scale(original: bytes, converted: fitz.Document) -> float:
    """How much the ink was scaled, measured on the rendered result."""
    src = fitz.open("pdf", original)
    before = _content_bbox(src[0])
    src.close()
    after = _content_bbox(converted[0])
    return after.width / before.width


class PageSizeTests(TestCase):
    def test_output_is_the_requested_sheet(self):
        for name, (width, height) in PAGE_SIZES.items():
            with self.subTest(target=name):
                doc = _convert(_make_pdf(), target_size=name)
                rect = doc[0].rect
                doc.close()
                self.assertAlmostEqual(rect.width, width, delta=1.0)
                self.assertAlmostEqual(rect.height, height, delta=1.0)

    def test_a4_to_letter_keeps_full_scale_when_margins_allow(self):
        """A4 loses 8.8 mm top and bottom on Letter, so a 12 mm margin fits."""
        data = _make_pdf(size=A4, margin_mm=12.0)
        doc = _convert(data, target_size="letter", mode="auto")
        try:
            self.assertAlmostEqual(_ink_scale(data, doc), 1.0, delta=0.01)
        finally:
            doc.close()

    def test_a4_to_letter_shrinks_instead_of_cropping_tight_margins(self):
        """A 3 mm margin cannot survive at 100%, so it must scale down."""
        data = _make_pdf(size=A4, margin_mm=3.0)
        doc = _convert(data, target_size="letter", mode="auto")
        try:
            scale = _ink_scale(data, doc)
            self.assertLess(scale, 1.0)
            # Nothing may be lost: the ink box must still be inside the sheet.
            box = _content_bbox(doc[0])
            self.assertGreaterEqual(box.x0, -1.0)
            self.assertGreaterEqual(box.y0, -1.0)
            self.assertLessEqual(box.x1, LETTER[0] + 1.0)
            self.assertLessEqual(box.y1, LETTER[1] + 1.0)
        finally:
            doc.close()

    def test_full_bleed_page_is_scaled_not_cropped(self):
        data = _make_pdf(size=A4, margin_mm=12.0, full_bleed=True)
        doc = _convert(data, target_size="letter", mode="auto")
        try:
            self.assertLess(_ink_scale(data, doc), 1.0)
        finally:
            doc.close()

    def test_every_page_gets_the_same_scale(self):
        """One page with no room must shrink the whole document, evenly.

        Otherwise a planner prints with the grid drifting between sheets.
        """
        doc = fitz.open()
        for margin_mm in (12.0, 2.0, 12.0):
            page = doc.new_page(width=A4[0], height=A4[1])
            margin = margin_mm * MM
            page.draw_rect(
                fitz.Rect(margin, margin, A4[0] - margin, A4[1] - margin),
                color=(0, 0, 0),
                width=1.2,
            )
        data = doc.write()
        doc.close()

        out = _convert(data, target_size="letter", mode="auto")
        try:
            widths = [_content_bbox(page).width for page in out]
            # Pages 1 and 3 are identical drawings, so identical output widths.
            self.assertAlmostEqual(widths[0], widths[2], delta=1.0)
            # And the roomy pages were shrunk too, not left at 100%.
            src = fitz.open("pdf", data)
            original = _content_bbox(src[0]).width
            src.close()
            self.assertLess(widths[0], original)
        finally:
            out.close()

    def test_fit_mode_always_scales_page_to_sheet(self):
        data = _make_pdf(size=A4, margin_mm=12.0)
        doc = _convert(data, target_size="letter", mode="fit")
        try:
            # A4 -> Letter fit factor is 792/841.89 = 0.94, applied regardless
            # of how much room the margins left.
            self.assertAlmostEqual(_ink_scale(data, doc), 0.94, delta=0.02)
        finally:
            doc.close()

    def test_letter_to_a4_fits_at_full_scale(self):
        """A4 is taller, so the only cost is 3 mm a side; 12 mm covers it."""
        data = _make_pdf(size=LETTER, margin_mm=12.0)
        doc = _convert(data, target_size="a4", mode="auto")
        try:
            self.assertAlmostEqual(_ink_scale(data, doc), 1.0, delta=0.01)
        finally:
            doc.close()

    def test_blank_page_does_not_crash(self):
        doc = fitz.open()
        doc.new_page(width=A4[0], height=A4[1])
        data = doc.write()
        doc.close()

        out = _convert(data, target_size="letter")
        try:
            self.assertAlmostEqual(out[0].rect.width, LETTER[0], delta=1.0)
        finally:
            out.close()

    def test_page_count_is_preserved(self):
        doc = _convert(_make_pdf(pages=5), target_size="legal")
        try:
            self.assertEqual(doc.page_count, 5)
        finally:
            doc.close()

    def test_unknown_size_is_rejected_at_the_boundary(self):
        with self.assertRaises(InvalidPDFError):
            resize_pdf(_upload(_make_pdf()), target_size="tabloid")

    def test_unknown_mode_is_rejected_at_the_boundary(self):
        with self.assertRaises(InvalidPDFError):
            resize_pdf(_upload(_make_pdf()), mode="stretch")


class ResizePDFAPITests(TestCase):
    def setUp(self):
        # Anonymous rate-limit counters live in the shared cache, so without a
        # wipe the second request in this class 429s.
        cache.clear()

    def test_endpoint_returns_pdf_on_the_requested_sheet(self):
        client = Client()
        resp = client.post(
            "/api/pdf-edit/page-size/",
            {"pdf_file": _upload(_make_pdf()), "target_size": "letter"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        body = b"".join(resp.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))

        doc = fitz.open("pdf", body)
        try:
            self.assertAlmostEqual(doc[0].rect.width, LETTER[0], delta=1.0)
            self.assertAlmostEqual(doc[0].rect.height, LETTER[1], delta=1.0)
        finally:
            doc.close()

    def test_endpoint_rejects_unknown_size(self):
        client = Client()
        resp = client.post(
            "/api/pdf-edit/page-size/",
            {"pdf_file": _upload(_make_pdf()), "target_size": "tabloid"},
        )
        # The serializer's ChoiceField catches it before any work is done.
        self.assertEqual(resp.status_code, 400)

    def test_tool_page_ships_the_config_the_js_needs(self):
        """The page is useless without these three, and both have bitten before.

        A template that overrides extra_js without block.super drops
        window.API_URL and the tool silently posts to the page URL; the option
        selects only reach the API because the generic script collects form
        fields by name.
        """
        resp = Client().get("/en/pdf-edit/page-size/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # escapejs turns the hyphens into -, so compare on decoded JS.
        api_url = re.search(r'window\.API_URL = "([^"]*)"', html)
        self.assertIsNotNone(api_url, "window.API_URL missing from the page")
        self.assertEqual(
            api_url.group(1).encode().decode("unicode_escape"),
            "/api/pdf-edit/page-size/",
        )
        self.assertIn('name="target_size"', html)
        self.assertIn('name="mode"', html)

    def test_endpoint_defaults_to_letter(self):
        client = Client()
        resp = client.post(
            "/api/pdf-edit/page-size/", {"pdf_file": _upload(_make_pdf())}
        )
        self.assertEqual(resp.status_code, 200)
        doc = fitz.open("pdf", b"".join(resp.streaming_content))
        try:
            self.assertAlmostEqual(doc[0].rect.width, LETTER[0], delta=1.0)
        finally:
            doc.close()
