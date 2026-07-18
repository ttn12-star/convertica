"""EPUB conversion utility functions."""

from __future__ import annotations

import html
import os
import re
import tempfile
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import fitz
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from src.api.font_utils import detect_script, register_font_for_script, shape_rtl
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError

logger = get_logger(__name__)


def _read_member_capped(epub: zipfile.ZipFile, name: str) -> bytes:
    """Decompress one EPUB (ZIP) member with a hard uncompressed-size ceiling.

    EPUB is a ZIP container reachable by anonymous free users. Both the declared
    per-member/total sizes (guarded in _parse_epub_structure) and the ACTUAL
    decompressed bytes must be bounded: a crafted member can declare a tiny size
    yet expand to GBs, OOM-killing sibling conversions that share the worker
    cgroup. Reading cap+1 bytes and rejecting on overflow stops that. Mirrors
    archive_tools.read_member_capped; reuses the ARCHIVE_MAX_* limits.
    """
    cap = getattr(settings, "ARCHIVE_MAX_MEMBER_UNCOMPRESSED", 200 * 1024 * 1024)
    with epub.open(name) as src:
        data = src.read(cap + 1)
    if len(data) > cap:
        raise InvalidPDFError("An entry inside the EPUB is too large to process.")
    return data


def _normalize_whitespace(value: str) -> str:
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _strip_html_to_text(content: str) -> str:
    """Extract plain text from XHTML/HTML content with basic block handling."""
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", content)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(
        r"(?i)</(p|div|section|article|li|h[1-6]|tr|blockquote)>",
        "\n\n",
        cleaned,
    )
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return _normalize_whitespace(cleaned)


def _safe_fromstring(data: bytes):
    """Parse XML, rejecting any DOCTYPE.

    ElementTree expands internal entities (billion-laughs DoS) and the XML here
    is attacker-controlled zip content. EPUB container.xml / .opf never carry a
    DOCTYPE, so refusing one closes the entity-expansion vector with no new dep.
    """
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ConversionError(
            "Invalid EPUB structure: XML document type declarations are not allowed."
        )
    return ET.fromstring(data)


def _guard_epub_zip(epub: zipfile.ZipFile) -> None:
    """Reject EPUBs whose declared member count/uncompressed sizes are bombs.

    First line of defense (declared central-directory sizes); _read_member_capped
    is the second (actual decompressed bytes). Reuses the shared ARCHIVE_MAX_*.
    """
    infos = epub.infolist()
    max_members = getattr(settings, "ARCHIVE_MAX_MEMBERS", 2000)
    max_member = getattr(settings, "ARCHIVE_MAX_MEMBER_UNCOMPRESSED", 200 * 1024 * 1024)
    max_total = getattr(settings, "ARCHIVE_MAX_TOTAL_UNCOMPRESSED", 500 * 1024 * 1024)
    if len(infos) > max_members:
        raise InvalidPDFError("EPUB has too many internal files to process.")
    total = 0
    for zi in infos:
        if zi.file_size > max_member:
            raise InvalidPDFError("An entry inside the EPUB is too large to process.")
        total += zi.file_size
    if total > max_total:
        raise InvalidPDFError("EPUB contents are too large to process.")


def _parse_epub_structure(epub_path: str) -> tuple[list[str], str]:
    """Read EPUB and return ordered chapter texts and title."""
    try:
        epub = zipfile.ZipFile(epub_path, "r")
    except zipfile.BadZipFile as exc:
        raise InvalidPDFError("File is not a valid EPUB (not a ZIP archive).") from exc
    with epub:
        _guard_epub_zip(epub)
        opf_path = None
        if "META-INF/container.xml" in epub.namelist():
            container_xml = _read_member_capped(epub, "META-INF/container.xml")
            root = _safe_fromstring(container_xml)
            rootfile = root.find(".//{*}rootfile")
            if rootfile is not None:
                opf_path = rootfile.attrib.get("full-path")

        if not opf_path:
            opf_candidates = [name for name in epub.namelist() if name.endswith(".opf")]
            if not opf_candidates:
                raise InvalidPDFError("Invalid EPUB structure: OPF manifest not found.")
            opf_path = opf_candidates[0]

        opf_data = _read_member_capped(epub, opf_path)
        opf_root = _safe_fromstring(opf_data)
        ns = {"opf": opf_root.tag.split("}")[0].strip("{")}

        title_node = opf_root.find(".//{*}title")
        book_title = (
            title_node.text.strip()
            if title_node is not None and title_node.text
            else ""
        )
        if not book_title:
            book_title = Path(epub_path).stem

        manifest_items: dict[str, str] = {}
        for item in opf_root.findall(".//opf:manifest/opf:item", ns):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if item_id and href:
                manifest_items[item_id] = href

        spine_ids = [
            itemref.attrib.get("idref")
            for itemref in opf_root.findall(".//opf:spine/opf:itemref", ns)
            if itemref.attrib.get("idref")
        ]

        opf_dir = os.path.dirname(opf_path)
        chapter_texts: list[str] = []

        for spine_id in spine_ids:
            href = manifest_items.get(spine_id)
            if not href:
                continue
            chapter_path = os.path.normpath(os.path.join(opf_dir, href)).replace(
                "\\", "/"
            )
            if chapter_path not in epub.namelist():
                continue
            chapter_bytes = _read_member_capped(epub, chapter_path)
            chapter_html = chapter_bytes.decode("utf-8", errors="ignore")
            chapter_text = _strip_html_to_text(chapter_html)
            if chapter_text:
                chapter_texts.append(chapter_text)

        if not chapter_texts:
            raise InvalidPDFError("EPUB does not contain readable text content.")

        return chapter_texts, book_title


def convert_epub_to_pdf(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert EPUB to PDF and return (input_path, output_path)."""
    context = {
        "function": "convert_epub_to_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }
    logger.info("Starting EPUB to PDF conversion", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="epub_to_pdf_")
    safe_name = get_valid_filename(os.path.basename(uploaded_file.name))
    input_path = os.path.join(tmp_dir, safe_name)

    try:
        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        chapter_texts, book_title = _parse_epub_structure(input_path)

        output_name = f"{Path(safe_name).stem}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        # Pick the font from the book's dominant script so non-Latin ebooks
        # (Cyrillic/Arabic/CJK/Devanagari) render real glyphs, not tofu.
        sample_text = book_title + "\n" + "\n".join(chapter_texts[:3])
        script = detect_script(sample_text)
        font_regular, font_bold = register_font_for_script(script)
        is_rtl = script == "arabic"
        align = TA_RIGHT if is_rtl else TA_LEFT

        def _fmt(text: str) -> str:
            # Shape Arabic (join + RTL reorder) before escaping; no-op otherwise.
            return escape(shape_rtl(text))

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "BookTitle",
            parent=styles["Title"],
            fontName=font_bold,
            fontSize=20,
            leading=24,
            spaceAfter=14,
            alignment=align,
        )
        heading_style = ParagraphStyle(
            "ChapterHeading",
            parent=styles["Heading2"],
            fontName=font_bold,
            fontSize=14,
            leading=18,
            spaceBefore=8,
            spaceAfter=8,
            alignment=align,
        )
        body_style = ParagraphStyle(
            "BodyTextCompact",
            parent=styles["BodyText"],
            fontName=font_regular,
            fontSize=10.5,
            leading=14,
            spaceAfter=7,
            alignment=align,
        )

        story = [Paragraph(_fmt(book_title), title_style), Spacer(1, 8)]
        for index, chapter in enumerate(chapter_texts, start=1):
            story.append(Paragraph(_fmt(f"Chapter {index}"), heading_style))
            for paragraph in chapter.split("\n\n"):
                para = paragraph.strip()
                if not para:
                    continue
                story.append(Paragraph(_fmt(para), body_style))
            story.append(Spacer(1, 6))

        doc.build(story)
        logger.info(
            "EPUB to PDF conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
                "chapters": len(chapter_texts),
            },
        )
        return input_path, output_path
    except ConversionError:
        # InvalidPDFError/EncryptedPDFError etc. are user-input faults (→400).
        # Let them propagate unchanged instead of masking them as a 500.
        raise
    except Exception as exc:
        logger.exception(
            "EPUB to PDF conversion failed", extra={**context, "error": str(exc)}
        )
        raise ConversionError(f"Failed to convert EPUB to PDF: {exc}") from exc


def _chunk_pages_for_epub(
    page_texts: list[str], pages_per_chapter: int = 15
) -> list[str]:
    chunks: list[str] = []
    for start in range(0, len(page_texts), pages_per_chapter):
        part = page_texts[start : start + pages_per_chapter]
        chunks.append("\n\n".join(part))
    return chunks


def _text_to_xhtml(content: str) -> str:
    paragraphs = [
        segment.strip() for segment in re.split(r"\n\s*\n", content) if segment.strip()
    ]
    if not paragraphs:
        paragraphs = ["No text extracted from source pages."]
    body = []
    for paragraph in paragraphs:
        escaped = escape(paragraph).replace("\n", "<br/>")
        body.append(f"<p>{escaped}</p>")
    return "\n".join(body)


def _build_epub_archive(output_path: str, title: str, chapters: list[str]):
    book_uuid = str(uuid.uuid4())
    chapter_files = [f"chapter_{idx + 1}.xhtml" for idx in range(len(chapters))]

    nav_links = "\n".join(
        f'<li><a href="{name}">Chapter {idx + 1}</a></li>'
        for idx, name in enumerate(chapter_files)
    )
    nav_doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="style.css" type="text/css" />
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>{escape(title)}</h1>
    <ol>
      {nav_links}
    </ol>
  </nav>
</body>
</html>
"""

    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    spine_items = []
    for idx, chapter_file in enumerate(chapter_files):
        chapter_id = f"chap{idx + 1}"
        manifest_items.append(
            f'<item id="{chapter_id}" href="{chapter_file}" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="{chapter_id}"/>')

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{book_uuid}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    {' '.join(manifest_items)}
  </manifest>
  <spine>
    {' '.join(spine_items)}
  </spine>
</package>
"""

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    stylesheet = """body { font-family: serif; line-height: 1.5; margin: 5%; }
h1 { font-size: 1.4em; margin-bottom: 1em; }
p { margin-bottom: 0.8em; }
"""

    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr(
            "META-INF/container.xml",
            container_xml,
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/content.opf",
            content_opf,
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            nav_doc,
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/style.css",
            stylesheet,
            compress_type=zipfile.ZIP_DEFLATED,
        )

        for idx, chapter_text in enumerate(chapters):
            chapter_content = _text_to_xhtml(chapter_text)
            chapter_doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Chapter {idx + 1}</title>
  <link rel="stylesheet" href="style.css" type="text/css" />
</head>
<body>
  <h1>Chapter {idx + 1}</h1>
  {chapter_content}
</body>
</html>
"""
            archive.writestr(
                f"OEBPS/chapter_{idx + 1}.xhtml",
                chapter_doc,
                compress_type=zipfile.ZIP_DEFLATED,
            )


def convert_pdf_to_epub(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF to EPUB and return (input_path, output_path)."""
    context = {
        "function": "convert_pdf_to_epub",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }
    logger.info("Starting PDF to EPUB conversion", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_epub_")
    safe_name = get_valid_filename(os.path.basename(uploaded_file.name))
    input_path = os.path.join(tmp_dir, safe_name)

    try:
        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        try:
            doc = fitz.open(input_path)
        except Exception as exc:
            # Corrupt / non-PDF renamed .pdf is user input, not a server fault.
            raise InvalidPDFError(
                "File is not a valid PDF and cannot be converted."
            ) from exc
        page_texts: list[str] = []
        for page_index, page in enumerate(doc, start=1):
            text = _normalize_whitespace(page.get_text("text"))
            if not text:
                text = "No extractable text on this page."
            page_texts.append(f"Page {page_index}\n{text}")
        doc.close()

        if not page_texts:
            raise ConversionError("PDF does not contain extractable text content.")

        chapters = _chunk_pages_for_epub(page_texts, pages_per_chapter=15)
        output_name = f"{Path(safe_name).stem}{suffix}.epub"
        output_path = os.path.join(tmp_dir, output_name)
        title = Path(safe_name).stem.replace("_", " ").strip() or "Converted Book"
        _build_epub_archive(output_path, title=title, chapters=chapters)

        logger.info(
            "PDF to EPUB conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
                "pages": len(page_texts),
                "chapters": len(chapters),
            },
        )
        return input_path, output_path
    except ConversionError:
        # InvalidPDFError etc. are user-input faults (→400); don't mask as 500.
        raise
    except Exception as exc:
        logger.exception(
            "PDF to EPUB conversion failed", extra={**context, "error": str(exc)}
        )
        raise ConversionError(f"Failed to convert PDF to EPUB: {exc}") from exc
