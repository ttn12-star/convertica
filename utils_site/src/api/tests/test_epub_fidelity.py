"""EPUB fidelity: conversions must carry structure and images, not just text.

Regression cover for the "formatting and images are lost" reports: both
directions used to flatten the document to a plain-text stream.
"""

import io
import xml.etree.ElementTree as ET
import zipfile

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from src.api.epub_convert.utils import convert_epub_to_pdf, convert_pdf_to_epub


def _red_png() -> bytes:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 80))
    pix.set_rect(pix.irect, (220, 40, 40))
    return pix.tobytes("png")


def _rich_pdf() -> SimpleUploadedFile:
    """A PDF with a heading, a bold run, wrapped body lines and an image.

    Lines are drawn 20pt apart at 11.5pt so MuPDF reports each one as its own
    block — the layout that used to become one <p> per visual line.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((60, 70), "The Chapter Heading", fontsize=22, fontname="hebo")
    page.insert_text(
        (60, 120), "Revenue grew steadily over the quarter and", fontsize=11.5
    )
    page.insert_text(
        (60, 140), "the trend continued into the second half.", fontsize=11.5
    )
    page.insert_htmlbox(
        fitz.Rect(60, 175, 500, 215),
        '<p style="font-size:11.5px">Plain words with <b>emphasis</b> inside one long body sentence that keeps going.</p>',
    )
    page.insert_image(fitz.Rect(60, 220, 300, 380), stream=_red_png())
    buffer = io.BytesIO(doc.tobytes())
    return SimpleUploadedFile(
        "rich.pdf", buffer.getvalue(), content_type="application/pdf"
    )


def _rich_epub() -> SimpleUploadedFile:
    chapter = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        "<h1>Настоящий заголовок</h1>"
        "<p>Text with <b>bold</b> and <i>italic</i>.</p>"
        '<p><img src="images/pic.png" alt="pic"/></p>'
        "</body></html>"
    )
    opf = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="b">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="b">u1</dc:identifier><dc:title>Test Book</dc:title></metadata>'
        '<manifest><item id="c" href="chapter1.xhtml" media-type="application/xhtml+xml"/>'
        '<item id="i" href="images/pic.png" media-type="image/png"/></manifest>'
        '<spine><itemref idref="c"/></spine></package>'
    )
    container = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter1.xhtml", chapter)
        archive.writestr("OEBPS/images/pic.png", _red_png())
    return SimpleUploadedFile(
        "book.epub", buffer.getvalue(), content_type="application/epub+zip"
    )


class EpubFidelityTests(SimpleTestCase):
    def test_pdf_to_epub_keeps_headings_bold_and_images(self):
        _, output_path = convert_pdf_to_epub(_rich_pdf())
        with zipfile.ZipFile(output_path) as epub:
            names = epub.namelist()
            chapter = epub.read("OEBPS/chapter_1.xhtml").decode()
            opf = epub.read("OEBPS/content.opf").decode()

        images = [n for n in names if n.startswith("OEBPS/images/")]
        self.assertTrue(images, "PDF image was dropped instead of embedded")
        self.assertIn('media-type="image/png"', opf)
        self.assertIn("<h1>", chapter)
        self.assertIn("<b>emphasis</b>", chapter)
        # Wrapped lines must reflow as ONE paragraph, not one <p> per line.
        self.assertIn(
            "Revenue grew steadily over the quarter and the trend continued",
            chapter,
        )
        # Strict readers reject malformed XHTML outright.
        ET.fromstring(chapter)

    def test_epub_to_pdf_keeps_headings_and_images(self):
        _, output_path = convert_epub_to_pdf(_rich_epub())
        with fitz.open(output_path) as pdf:
            text = pdf[0].get_text()
            image_count = len(pdf[0].get_images())
        self.assertIn("Настоящий заголовок", text)
        self.assertIn("bold", text)
        self.assertEqual(image_count, 1, "EPUB image was dropped from the PDF")
