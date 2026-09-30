"""PDF to Markdown: reading order of columns and list markers.

Sorting lines by (y, x) interleaved two text columns line by line, and
Chromium draws ``<ul>`` bullets as small paths that never reach the text
layer, so list items came out as plain lines.
"""

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.pdf_convert.pdf_to_markdown.utils import convert_pdf_to_markdown

LEFT = [
    "Revenue grew 11.4% quarter over quarter, driven by the",
    "West region and a strong first full quarter for the online",
    "store. East was the only region to decline, after two",
]
RIGHT = [
    "Gross margin held at 38%. Shipping costs rose 6% on fuel",
    "surcharges, offset by lower packaging spend after the",
    "supplier switch in July.",
]


def _convert(page_builder) -> str:
    doc = fitz.open()
    page_builder(doc.new_page())
    data = doc.tobytes()
    doc.close()
    upload = SimpleUploadedFile("doc.pdf", data, content_type="application/pdf")
    _, output_path = convert_pdf_to_markdown(upload)
    with open(output_path, encoding="utf-8") as handle:
        return handle.read()


class PdfToMarkdownLayoutTests(SimpleTestCase):
    def test_two_columns_are_read_one_after_the_other(self):
        def build(page):
            page.insert_text((40, 60), "Summary", fontsize=16)
            # Right column starts a little higher, as Chromium lays it out.
            for i, line in enumerate(LEFT):
                page.insert_text((40, 110 + i * 16), line, fontsize=10)
            for i, line in enumerate(RIGHT):
                page.insert_text((310, 100 + i * 16), line, fontsize=10)

        markdown = _convert(build)

        self.assertIn("\n".join(LEFT + RIGHT), markdown)

    def test_vector_bullets_become_markdown_list_items(self):
        def build(page):
            page.insert_text(
                (40, 60), "Next quarter plan for all regions:", fontsize=10
            )
            for i, item in enumerate(["Reopen East", "Hire a manager"]):
                y = 90 + i * 16
                page.draw_circle((52, y - 3.5), 1.5, color=(0, 0, 0), fill=(0, 0, 0))
                page.insert_text((62, y), item, fontsize=10)
            page.insert_text((50, 140), "1. First step", fontsize=10)
            page.insert_text((40, 180), "Closing paragraph.", fontsize=10)

        markdown = _convert(build)

        self.assertIn("- Reopen East\n- Hire a manager\n1. First step\n\n", markdown)
        self.assertIn("\n\nClosing paragraph.", markdown)
