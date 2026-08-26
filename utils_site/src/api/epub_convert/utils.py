"""EPUB conversion utility functions."""

from __future__ import annotations

import collections
import hashlib
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


def _parse_epub_structure(epub_path: str) -> str:
    """Validate the EPUB container and return the book title.

    Rendering itself is MuPDF's job (it reads the ZIP again with its own HTML/CSS
    engine), so this only has to do what MuPDF won't: enforce our zip-bomb limits
    and turn a malformed container into a 400 instead of a 500.
    """
    try:
        epub = zipfile.ZipFile(epub_path, "r")
    except zipfile.BadZipFile as exc:
        raise InvalidPDFError("File is not a valid EPUB (not a ZIP archive).") from exc
    with epub:
        _guard_epub_zip(epub)
        names = epub.namelist()
        opf_path = None
        if "META-INF/container.xml" in names:
            root = _safe_fromstring(_read_member_capped(epub, "META-INF/container.xml"))
            rootfile = root.find(".//{*}rootfile")
            if rootfile is not None:
                opf_path = rootfile.attrib.get("full-path")
        if not opf_path or opf_path not in names:
            opf_candidates = [name for name in names if name.endswith(".opf")]
            if not opf_candidates:
                raise InvalidPDFError("Invalid EPUB structure: OPF manifest not found.")
            opf_path = opf_candidates[0]

        opf_root = _safe_fromstring(_read_member_capped(epub, opf_path))
        title_node = opf_root.find(".//{*}title")
        title = (
            title_node.text.strip()
            if title_node is not None and title_node.text
            else ""
        )
        return title or Path(epub_path).stem


def convert_epub_to_pdf(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert EPUB to PDF and return (input_path, output_path).

    MuPDF opens EPUB natively and lays it out with its own HTML/CSS engine, so
    headings, bold/italic, lists, tables, colours and embedded images survive —
    which flattening the book to plain text and re-typesetting it did not. Its
    bundled font set also covers Cyrillic/Arabic/CJK/Devanagari without relying
    on OS fonts, so no per-script font juggling is needed here.
    """
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

        title = _parse_epub_structure(input_path)

        output_name = f"{Path(safe_name).stem}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)

        try:
            book = fitz.open(input_path, filetype="epub")
        except Exception as exc:
            raise InvalidPDFError(
                "File is not a valid EPUB and cannot be converted."
            ) from exc

        with book:
            book.layout(rect=fitz.paper_rect("a4"), fontsize=11)
            if book.page_count < 1:
                raise InvalidPDFError("EPUB does not contain readable content.")
            max_pages = getattr(settings, "EPUB_MAX_PDF_PAGES", 3000)
            if book.page_count > max_pages:
                # A 50MB text-only EPUB reflows to tens of thousands of pages;
                # building that PDF in memory OOM-kills the sibling conversions
                # sharing the worker cgroup.
                raise InvalidPDFError("EPUB is too long to convert to PDF.")
            pdf_bytes = book.convert_to_pdf()

        with fitz.open("pdf", pdf_bytes) as pdf:
            pdf.set_metadata({"title": title, "producer": "Convertica"})
            pdf.save(output_path, garbage=3, deflate=True)

        logger.info(
            "EPUB to PDF conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
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


# --------------------------------------------------------------------------- #
# PDF -> EPUB
# --------------------------------------------------------------------------- #

# XML 1.0 forbids these control chars outright; PDF text streams do contain
# them, and a single one makes the whole EPUB unreadable in strict readers.
_XML_INVALID = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SENTENCE_END = (".", "!", "?", ":", ";", "…", "”", '"', "»", "’")
_LIST_START = re.compile(r"^\s*(?:[•◦▪‣●·*\-–—]\s|\(?\d{1,3}[.)]\s)")
_IMAGE_MEDIA = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif"}
_BOLD_TAG = re.compile(r"</?b>")
_SPAN_ITALIC = 1 << 1
_SPAN_BOLD = 1 << 4


def _modal_font_size(doc: fitz.Document) -> float:
    """Most-used font size in the document = its body-text size.

    Heading levels are decided relative to this, because "big" is only
    meaningful next to the body text: 12pt is a heading in a 9pt report and
    body text in a 12pt novel.
    """
    counter: collections.Counter[float] = collections.Counter()
    for page in doc.pages(0, min(doc.page_count, 30)):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    counter[round(span["size"] * 2) / 2] += len(span["text"].strip())
    return counter.most_common(1)[0][0] if counter else 11.0


def _join_lines(htmls: list[str], plains: list[str]) -> tuple[str, str]:
    """Join the visual lines of one paragraph, undoing hyphenation."""
    html, plain = htmls[0], plains[0]
    for extra_html, extra_plain in zip(htmls[1:], plains[1:], strict=True):
        if plain.rstrip().endswith("-"):
            if html.rstrip().endswith("-"):
                html = html.rstrip()[:-1]
            html += extra_html
            plain = plain.rstrip()[:-1] + extra_plain
        else:
            html = html.rstrip() + " " + extra_html
            plain = plain.rstrip() + " " + extra_plain
    return html, plain


def _text_block_to_item(block: dict, modal: float) -> dict | None:
    """Turn one PDF text block into one heading/paragraph candidate."""
    htmls: list[str] = []
    plains: list[str] = []
    max_size = 0.0
    bold_chars = 0
    total_chars = 0

    for line in block.get("lines", []):
        line_html: list[str] = []
        line_plain: list[str] = []
        for span in line.get("spans", []):
            text = _XML_INVALID.sub("", span.get("text", ""))
            if not text:
                continue
            flags = span.get("flags", 0)
            markup = escape(text)
            if flags & _SPAN_BOLD:
                markup = f"<b>{markup}</b>"
            if flags & _SPAN_ITALIC:
                markup = f"<i>{markup}</i>"
            line_html.append(markup)
            line_plain.append(text)
            max_size = max(max_size, span.get("size", 0.0))
            stripped = len(text.strip())
            total_chars += stripped
            if flags & _SPAN_BOLD:
                bold_chars += stripped
        if line_plain:
            htmls.append("".join(line_html))
            plains.append("".join(line_plain))

    if not total_chars:
        return None

    html, plain = _join_lines(htmls, plains)
    html, plain = html.strip(), plain.strip()
    size = max_size or modal
    mostly_bold = bold_chars / total_chars > 0.8
    if size >= modal * 1.5:
        tag = "h1"
    elif size >= modal * 1.25:
        tag = "h2"
    elif size >= modal * 1.08 or (mostly_bold and len(plain) <= 80):
        tag = "h3"
    else:
        tag = "p"
    return {
        "tag": tag,
        "html": html,
        "text": plain,
        "size": size,
        "top": block["bbox"][1],
        "bottom": block["bbox"][3],
    }


def _merge_wrapped(items: list[dict]) -> list[dict]:
    """Re-join blocks that are only the wrapped lines of a single paragraph.

    PDF has no paragraphs, and generously-leaded text makes MuPDF report every
    visual line as its own block. Emitting one <p> per line reflows terribly on
    a phone-sized reader, which is the bulk of the "formatting is lost" reports.

    ponytail: punctuation + geometry heuristic, sized for prose. A real layout
    analyser (columns, drop caps, running heads) is the upgrade path if
    multi-column PDFs start showing up in complaints.
    """
    merged: list[dict] = []
    for item in items:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and prev["tag"] == "p"
            and item["tag"] == "p"
            and abs(prev["size"] - item["size"]) < 1.0
            and 0 <= item["top"] - prev["bottom"] <= item["size"] * 1.6
            and not prev["text"].rstrip().endswith(_SENTENCE_END)
            and not _LIST_START.match(item["text"])
        ):
            prev["html"], prev["text"] = _join_lines(
                [prev["html"], item["html"]], [prev["text"], item["text"]]
            )
            prev["bottom"] = item["bottom"]
            continue
        merged.append(item)
    return merged


def _store_image(block: dict, sink: dict) -> str | None:
    """Save one PDF image block into the EPUB image sink; return its filename."""
    data = block.get("image")
    if not data:
        return None
    x0, y0, x1, y1 = block["bbox"]
    if (x1 - x0) < 8 or (y1 - y0) < 8:
        return None  # hairlines and spacer pixels, not illustrations

    ext = (block.get("ext") or "").lower()
    ext = "jpg" if ext in ("jpg", "jpeg") else ext
    if ext not in _IMAGE_MEDIA:
        # JPEG2000/TIFF/BMP are not EPUB core media types: re-encode to PNG.
        try:
            pix = fitz.Pixmap(data)
            if pix.colorspace is not None and pix.colorspace.n > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            data = pix.tobytes("png")
        except Exception:
            return None
        ext = "png"

    digest = hashlib.sha1(data).hexdigest()
    if digest in sink["seen"]:
        return sink["seen"][digest]  # logo/watermark repeated on every page
    if len(data) > sink["left"]:
        return None
    sink["left"] -= len(data)
    name = f"img{len(sink['files']) + 1}.{ext}"
    sink["files"][name] = data
    sink["seen"][digest] = name
    return name


def _page_to_xhtml(page, modal: float, sink: dict) -> tuple[str, str]:
    """Render one PDF page as an XHTML fragment; also return its first heading."""
    items: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 1:
            name = _store_image(block, sink)
            if name:
                # Keep the on-page proportion: without it every image reflows to
                # full width and an 80pt corner logo becomes a full-page plate.
                width = block["bbox"][2] - block["bbox"][0]
                pct = min(100, max(5, round(width / page.rect.width * 100)))
                items.append(
                    {
                        "tag": "img",
                        "html": f'<img src="images/{name}" alt="" style="width:{pct}%"/>',
                        "text": "",
                        "size": modal,
                        "top": block["bbox"][1],
                        "bottom": block["bbox"][3],
                    }
                )
            continue
        item = _text_block_to_item(block, modal)
        if item:
            items.append(item)

    parts: list[str] = []
    heading = ""
    for item in _merge_wrapped(items):
        if item["tag"] == "img":
            parts.append(f'<div class="image">{item["html"]}</div>')
            continue
        markup = item["html"]
        if item["tag"] != "p":
            markup = _BOLD_TAG.sub("", markup)  # headings are bold by themselves
        parts.append(f"<{item['tag']}>{markup}</{item['tag']}>")
        if not heading and item["tag"] in ("h1", "h2"):
            heading = item["text"]
    return "\n".join(parts), heading


def _chunk_pages_for_epub(
    page_texts: list[str], pages_per_chapter: int = 15
) -> list[str]:
    chunks: list[str] = []
    for start in range(0, len(page_texts), pages_per_chapter):
        part = page_texts[start : start + pages_per_chapter]
        chunks.append("\n\n".join(part))
    return chunks


def _build_epub_archive(
    output_path: str,
    title: str,
    chapters: list[str],
    images: dict[str, bytes] | None = None,
    labels: list[str] | None = None,
):
    """Write the EPUB 3 container. ``chapters`` are ready XHTML body fragments."""
    images = images or {}
    book_uuid = str(uuid.uuid4())
    chapter_files = [f"chapter_{idx + 1}.xhtml" for idx in range(len(chapters))]
    labels = labels or [f"Part {idx + 1}" for idx in range(len(chapters))]

    nav_links = "\n".join(
        f'<li><a href="{name}">{escape(labels[idx])}</a></li>'
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
    for idx, name in enumerate(images):
        media_type = _IMAGE_MEDIA[name.rsplit(".", 1)[-1]]
        manifest_items.append(
            f'<item id="img{idx + 1}" href="images/{name}" media-type="{media_type}"/>'
        )

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{book_uuid}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    {" ".join(manifest_items)}
  </manifest>
  <spine>
    {" ".join(spine_items)}
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
h1 { font-size: 1.5em; margin: 1em 0 0.6em; }
h2 { font-size: 1.25em; margin: 1em 0 0.5em; }
h3 { font-size: 1.1em; margin: 1em 0 0.4em; }
p { margin-bottom: 0.8em; text-align: justify; }
div.image { text-align: center; margin: 1em 0; }
div.image img { max-width: 100%; height: auto; }
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

        for idx, chapter_content in enumerate(chapters):
            chapter_doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{escape(labels[idx])}</title>
  <link rel="stylesheet" href="style.css" type="text/css" />
</head>
<body>
  {chapter_content}
</body>
</html>
"""
            archive.writestr(
                f"OEBPS/chapter_{idx + 1}.xhtml",
                chapter_doc,
                compress_type=zipfile.ZIP_DEFLATED,
            )

        for name, data in images.items():
            # Already-compressed formats: storing them again just burns CPU.
            archive.writestr(f"OEBPS/images/{name}", data, zipfile.ZIP_STORED)


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

        sink = {
            "files": {},
            "seen": {},
            "left": getattr(settings, "EPUB_MAX_IMAGE_BYTES", 60 * 1024 * 1024),
        }
        page_htmls: list[str] = []
        page_headings: list[str] = []
        with doc:
            modal = _modal_font_size(doc)
            for page in doc:
                html, heading = _page_to_xhtml(page, modal, sink)
                if html:
                    page_htmls.append(html)
                    page_headings.append(heading)

        if not page_htmls:
            raise ConversionError("PDF does not contain extractable text content.")

        pages_per_chapter = 15
        chapters = _chunk_pages_for_epub(page_htmls, pages_per_chapter)
        labels = []
        for start in range(0, len(page_htmls), pages_per_chapter):
            head = next(
                (h for h in page_headings[start : start + pages_per_chapter] if h), ""
            )
            labels.append(head or f"Part {len(labels) + 1}")

        output_name = f"{Path(safe_name).stem}{suffix}.epub"
        output_path = os.path.join(tmp_dir, output_name)
        title = Path(safe_name).stem.replace("_", " ").strip() or "Converted Book"
        _build_epub_archive(
            output_path,
            title=title,
            chapters=chapters,
            images=sink["files"],
            labels=labels,
        )

        logger.info(
            "PDF to EPUB conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
                "pages": len(page_htmls),
                "chapters": len(chapters),
                "images": len(sink["files"]),
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
