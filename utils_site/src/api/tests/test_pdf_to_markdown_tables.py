"""PDF to Markdown: a bordered page must not be exported as a one-cell table.

pdfplumber reports a "table" for any bordered box, so a framed page or a callout
used to swallow the whole text into a single Markdown cell — headings, paragraph
breaks and all. Real multi-column tables must still come through.
"""

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_convert.pdf_to_markdown.utils import convert_pdf_to_markdown


def _pdf_bytes(with_real_table: bool) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    # The frame that pdfplumber sees as a single-cell table.
    page.draw_rect(fitz.Rect(40, 40, 555, 780), width=1)
    page.insert_text((60, 80), "Quarterly Report", fontsize=20)
    # Several body lines so 11pt is unambiguously the body size and 20pt reads
    # as a heading.
    page.insert_text((60, 110), "Revenue by region.", fontsize=11)
    page.insert_text((60, 400), "All figures in USD thousands.", fontsize=11)
    page.insert_text((60, 420), "Prepared by the finance team.", fontsize=11)
    if with_real_table:
        cell_w, cell_h = 160, 24
        rows = [["Region", "Q1", "Q2"], ["EMEA", "120", "138"]]
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                rect = fitz.Rect(
                    60 + c * cell_w,
                    140 + r * cell_h,
                    60 + (c + 1) * cell_w,
                    140 + (r + 1) * cell_h,
                )
                page.draw_rect(rect, width=0.7)
                page.insert_text((rect.x0 + 6, rect.y1 - 8), cell, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _convert(data: bytes) -> str:
    upload = SimpleUploadedFile("doc.pdf", data, content_type="application/pdf")
    _, output_path = convert_pdf_to_markdown(upload)
    with open(output_path, encoding="utf-8") as handle:
        return handle.read()


class PdfToMarkdownTableTests(SimpleTestCase):
    def test_framed_page_keeps_prose_and_headings(self):
        markdown = _convert(_pdf_bytes(with_real_table=False))

        self.assertIn("# Quarterly Report", markdown)
        self.assertNotIn("| Quarterly Report", markdown)

    def test_real_table_is_still_exported_as_markdown(self):
        markdown = _convert(_pdf_bytes(with_real_table=True))

        self.assertIn("| Region | Q1 | Q2 |", markdown)
        self.assertIn("| EMEA | 120 | 138 |", markdown)
        self.assertIn("# Quarterly Report", markdown)
