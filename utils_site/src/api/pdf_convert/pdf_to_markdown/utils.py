"""PDF to Markdown conversion utilities."""

from __future__ import annotations

import os
import re
import tempfile
from collections import Counter
from pathlib import Path

import fitz
import pdfplumber
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _escape_markdown_cell(value: str) -> str:
    return _clean_text(value).replace("|", "\\|")


def _render_markdown_table(rows: list[list[str | None]]) -> str:
    normalized_rows: list[list[str]] = []
    for row in rows:
        if row is None:
            continue
        cleaned = [_escape_markdown_cell(cell or "") for cell in row]
        if any(cell for cell in cleaned):
            normalized_rows.append(cleaned)

    if not normalized_rows:
        return ""

    max_cols = max(len(row) for row in normalized_rows)
    # A one-column "table" carries no tabular information, and pdfplumber reports
    # one for any bordered box — a framed page or a callout swallowed the whole
    # text into a single cell, losing headings and paragraph breaks. Decline it so
    # the caller keeps the lines as prose.
    if max_cols < 2:
        return ""
    padded_rows = [row + [""] * (max_cols - len(row)) for row in normalized_rows]

    header = padded_rows[0]
    if not any(header):
        header = [f"Column {idx + 1}" for idx in range(max_cols)]

    table_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in padded_rows[1:]:
        table_lines.append("| " + " | ".join(row) + " |")
    return "\n".join(table_lines)


def _collect_heading_levels(document: fitz.Document) -> tuple[float, dict[float, int]]:
    font_sizes: list[float] = []
    for page in document:
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = _clean_text(span.get("text", ""))
                    if text:
                        font_sizes.append(round(float(span.get("size", 0.0)), 1))

    if not font_sizes:
        return 11.0, {}

    size_counter = Counter(font_sizes)
    body_size = float(size_counter.most_common(1)[0][0])
    heading_candidates = [
        size
        for size in sorted(size_counter.keys(), reverse=True)
        if size >= body_size * 1.15
    ]

    heading_levels: dict[float, int] = {}
    for index, size in enumerate(heading_candidates[:3], start=1):
        heading_levels[float(size)] = index

    return body_size, heading_levels


def _resolve_heading_level(
    line_text: str,
    line_font_size: float,
    body_size: float,
    heading_levels: dict[float, int],
) -> int | None:
    if not heading_levels:
        return None

    clean = _clean_text(line_text)
    if not clean:
        return None

    # Long lines are usually paragraphs, not headings.
    if len(clean) > 120 or len(clean.split()) > 16:
        return None

    if line_font_size < body_size * 1.12:
        return None

    closest_size = min(
        heading_levels.keys(), key=lambda size: abs(size - line_font_size)
    )
    if abs(closest_size - line_font_size) > 0.8:
        return None

    return heading_levels[closest_size]


def _bbox_is_inside_any_table(
    bbox: tuple[float, float, float, float],
    table_bboxes: list[tuple[float, float, float, float]],
) -> bool:
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    for tx0, ty0, tx1, ty1 in table_bboxes:
        if tx0 <= cx <= tx1 and ty0 <= cy <= ty1:
            return True
    return False


_BULLET_CHARS = "•◦▪▫■□●○‣⁃\uf0a7\uf0b7"  # U+F0xx: Symbol/Wingdings bullets from Word
_ORDERED_ITEM_RE = re.compile(r"^\d{1,3}[.)]\s")


def _vector_list_markers(page: fitz.Page) -> list[tuple[float, float, float, float]]:
    """Small dot/square shapes — how Chromium and others draw ``<ul>`` bullets.

    Such bullets are paths, not glyphs, so they never reach the text layer.
    """
    markers = []
    for kind, rect in page.get_bboxlog():
        if not kind.endswith("-path"):
            continue
        x0, y0, x1, y1 = rect
        width, height = x1 - x0, y1 - y0
        # ponytail: fixed 8pt ceiling, fine for body-size bullets; scale by line
        # height if giant-font lists turn up.
        if 0 < width <= 8 and 0 < height <= 8 and 0.5 <= width / height <= 2:
            markers.append((x0, y0, x1, y1))
    return markers


def _list_marker_x(
    bbox: tuple[float, float, float, float],
    markers: list[tuple[float, float, float, float]],
) -> float | None:
    """x of a bullet sitting just left of this line, vertically inside it."""
    x0, y0, _, y1 = bbox
    height = y1 - y0
    for mx0, my0, mx1, my1 in markers:
        if y0 <= (my0 + my1) / 2 <= y1 and x0 - 2 * height <= mx1 <= x0 + 1:
            return mx0
    return None


def _gutters(items: list[dict[str, object]], min_gap: float) -> list[float]:
    """x positions of vertical gaps that no item crosses (column gutters)."""
    spans = sorted((float(item["x"]), float(item["x1"])) for item in items)
    gutters = []
    right = spans[0][1]
    for x0, x1 in spans[1:]:
        if x0 - right >= min_gap:
            gutters.append(x0)
        right = max(right, x1)
    return gutters


def _column_of(item: dict[str, object], gutters: list[float]) -> int:
    return sum(1 for gutter in gutters if float(item["x"]) >= gutter)


def _is_real_column_layout(
    items: list[dict[str, object]], gutters: list[float], page_width: float
) -> bool:
    """Text columns, not a borderless table or a stray right-aligned line."""
    columns: list[list[dict[str, object]]] = [[] for _ in range(len(gutters) + 1)]
    for item in items:
        columns[_column_of(item, gutters)].append(item)
    for index, column in enumerate(columns):
        if not column:
            return False
        widest = max(float(i["x1"]) - float(i["x"]) for i in column)
        # Prose runs up to the gutter; cells of a borderless table
        # ("Region", "$412,300") leave most of their slot empty.
        if widest < page_width * 0.15:
            return False
        if index < len(gutters):
            slot = gutters[index] - min(float(i["x"]) for i in column)
            if widest < slot * 0.7:
                return False
    for left, right in zip(columns, columns[1:], strict=False):
        side_by_side = sum(
            1
            for a in left
            if any(
                float(a["y"]) < float(b["y1"]) and float(b["y"]) < float(a["y1"])
                for b in right
            )
        )
        if side_by_side < 2:
            return False
    return True


def _slab_continues_group(
    group: list[dict[str, object]], slab: list[dict[str, object]], min_gap: float
) -> bool:
    group_has_columns = bool(_gutters(group, min_gap))
    merged_gutters = _gutters(group + slab, min_gap)
    if not group_has_columns:
        # Plain text goes on until something side by side starts.
        return not _gutters(slab, min_gap) and not merged_gutters
    if not merged_gutters:
        return False  # a full-width line (heading, prose) ends the columns
    if _gutters(slab, min_gap):
        return True
    # Only one column has a line here: the tail of a longer column, or the
    # first short line (heading, paragraph) under the columns. A tail follows
    # its column at line spacing; what comes after the columns is further off.
    column = _column_of(slab[0], merged_gutters)
    column_bottom = max(
        (
            float(item["y1"])
            for item in group
            if _column_of(item, merged_gutters) == column
        ),
        default=float("-inf"),
    )
    line_height = max(float(item["y1"]) - float(item["y"]) for item in slab)
    return float(slab[0]["y"]) - column_bottom <= line_height * 0.6


def _reading_order(
    items: list[dict[str, object]], page_width: float, min_gap: float
) -> list[dict[str, object]]:
    """Order a page's lines and tables: top to bottom, but column by column.

    Sorting by (y, x) alone interleaves side-by-side columns line by line.
    Items are cut into horizontal slabs (runs of vertically overlapping
    items); consecutive slabs that share a gutter nobody crosses form one
    column group, read column after column. Full-width lines (headings,
    single-column prose) cross any gutter and end the group.
    """
    items = sorted(items, key=lambda item: (float(item["y"]), float(item["x"])))
    slabs: list[list[dict[str, object]]] = []
    bottom = float("-inf")
    for item in items:
        if slabs and float(item["y"]) < bottom:
            slabs[-1].append(item)
            bottom = max(bottom, float(item["y1"]))
        else:
            slabs.append([item])
            bottom = float(item["y1"])

    groups: list[list[dict[str, object]]] = []
    for slab in slabs:
        if groups and _slab_continues_group(groups[-1], slab, min_gap):
            groups[-1].extend(slab)
        else:
            groups.append(list(slab))

    ordered: list[dict[str, object]] = []
    for group in groups:
        gutters = _gutters(group, min_gap)
        if gutters and _is_real_column_layout(group, gutters, page_width):
            group.sort(
                key=lambda item: (
                    _column_of(item, gutters),
                    float(item["y"]),
                    float(item["x"]),
                )
            )
        ordered.extend(group)
    return ordered


def convert_pdf_to_markdown(
    uploaded_file: UploadedFile,
    detect_headings: bool = True,
    preserve_tables: bool = True,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF to Markdown with heading and table preservation."""
    context = {
        "function": "convert_pdf_to_markdown",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "detect_headings": detect_headings,
        "preserve_tables": preserve_tables,
    }

    logger.info("Starting PDF to Markdown conversion", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_markdown_")
    input_path = None
    output_path = None

    try:
        required_mb = max(100, int((uploaded_file.size * 6) / (1024 * 1024)))
        has_space, disk_error = check_disk_space(tmp_dir, required_mb=required_mb)
        if not has_space:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        safe_filename = sanitize_filename(get_valid_filename(uploaded_file.name))
        input_path = os.path.join(tmp_dir, safe_filename)

        with open(input_path, "wb") as file_obj:
            for chunk in uploaded_file.chunks():
                file_obj.write(chunk)

        is_valid, validation_error = validate_pdf_file(input_path, context)
        if not is_valid:
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        with fitz.open(input_path) as document:
            body_size, heading_levels = _collect_heading_levels(document)
            page_markdown_blocks: list[str] = []

            with pdfplumber.open(input_path) as plumber_doc:
                for page_index, page in enumerate(document):
                    text_items: list[dict[str, object]] = []
                    table_items: list[dict[str, object]] = []
                    table_bboxes: list[tuple[float, float, float, float]] = []

                    if preserve_tables:
                        plumber_page = plumber_doc.pages[page_index]
                        try:
                            for table in plumber_page.find_tables():
                                markdown_table = _render_markdown_table(table.extract())
                                if markdown_table:
                                    x0, y0, x1, y1 = tuple(float(v) for v in table.bbox)
                                    table_bboxes.append((x0, y0, x1, y1))
                                    table_items.append(
                                        {
                                            "type": "table",
                                            "x": x0,
                                            "y": y0,
                                            "x1": x1,
                                            "y1": y1,
                                            "text": markdown_table,
                                        }
                                    )
                        except Exception as table_error:  # noqa: BLE001
                            logger.warning(
                                "Table extraction warning",
                                extra={
                                    **context,
                                    "page": page_index + 1,
                                    "error": str(table_error),
                                },
                            )
                        finally:
                            # pdfplumber keeps every parsed char/edge of a page
                            # alive until the document closes; on a 200-page file
                            # that is ~1 GB, enough to OOM a celery worker and
                            # take its neighbour down with it.
                            plumber_page.flush_cache()
                            plumber_page.close()

                    list_markers = _vector_list_markers(page)
                    page_text_lines = []
                    blocks = page.get_text("dict").get("blocks", [])
                    for block in blocks:
                        if block.get("type") != 0:
                            continue

                        for line in block.get("lines", []):
                            spans = line.get("spans", [])
                            line_text = _clean_text(
                                "".join(span.get("text", "") for span in spans)
                            )
                            if not line_text:
                                continue

                            bbox = line.get("bbox")
                            if not bbox or len(bbox) != 4:
                                continue

                            bbox_tuple = tuple(float(value) for value in bbox)
                            if _bbox_is_inside_any_table(bbox_tuple, table_bboxes):
                                continue

                            if line_text in _BULLET_CHARS:
                                # The bullet glyph came out as its own line.
                                list_markers.append(bbox_tuple)
                                continue
                            page_text_lines.append((line_text, bbox_tuple, spans))

                    for line_text, bbox_tuple, spans in page_text_lines:
                        line_font_size = max(
                            (
                                round(float(span.get("size", body_size)), 1)
                                for span in spans
                                if _clean_text(span.get("text", ""))
                            ),
                            default=body_size,
                        )

                        heading_level = None
                        if detect_headings:
                            heading_level = _resolve_heading_level(
                                line_text=line_text,
                                line_font_size=line_font_size,
                                body_size=body_size,
                                heading_levels=heading_levels,
                            )

                        list_x = None
                        if heading_level:
                            markdown_line = f"{'#' * heading_level} {line_text}"
                        elif line_text[0] in _BULLET_CHARS:
                            list_x = bbox_tuple[0]
                            markdown_line = f"- {line_text[1:].strip()}"
                        elif _ORDERED_ITEM_RE.match(line_text):
                            list_x = bbox_tuple[0]
                            markdown_line = line_text
                        else:
                            list_x = _list_marker_x(bbox_tuple, list_markers)
                            markdown_line = (
                                line_text if list_x is None else f"- {line_text}"
                            )

                        text_items.append(
                            {
                                "type": "text",
                                "x": bbox_tuple[0],
                                "y": bbox_tuple[1],
                                "x1": bbox_tuple[2],
                                "y1": bbox_tuple[3],
                                "list_x": list_x,
                                "text": markdown_line,
                            }
                        )

                    merged_items = _reading_order(
                        [*text_items, *table_items],
                        page_width=page.rect.width,
                        min_gap=body_size * 0.8,
                    )

                    page_lines: list[str] = []
                    list_x = None  # marker x of the list we are inside, if any
                    for item in merged_items:
                        item_text = str(item["text"]).strip()
                        if not item_text:
                            continue

                        if item.get("list_x") is not None:
                            if list_x is None and page_lines and page_lines[-1] != "":
                                page_lines.append("")
                            list_x = float(item["list_x"])
                            page_lines.append(item_text)
                            continue
                        if list_x is not None:
                            if (
                                item["type"] == "text"
                                and not item_text.startswith("#")
                                and list_x + 1
                                < float(item["x"])
                                <= list_x + body_size * 4
                            ):
                                # Wrapped item text, indented past the marker.
                                # The upper bound keeps the next column (far
                                # right of the marker) out of the last item.
                                page_lines.append(f"  {item_text}")
                                continue
                            # Without a blank line the next paragraph would be
                            # swallowed into the last item as lazy continuation.
                            page_lines.append("")
                            list_x = None

                        if item["type"] == "table":
                            if page_lines and page_lines[-1] != "":
                                page_lines.append("")
                            page_lines.extend(item_text.splitlines())
                            page_lines.append("")
                            continue

                        if item_text.startswith("#"):
                            if page_lines and page_lines[-1] != "":
                                page_lines.append("")
                            page_lines.append(item_text)
                            page_lines.append("")
                        else:
                            page_lines.append(item_text)

                    page_content = re.sub(
                        r"\n{3,}",
                        "\n\n",
                        "\n".join(page_lines).strip(),
                    )

                    if not page_content:
                        page_content = "_No extractable text on this page._"

                    if len(document) > 1:
                        page_content = f"## Page {page_index + 1}\n\n{page_content}"
                    page_markdown_blocks.append(page_content)

        markdown_content = "\n\n---\n\n".join(page_markdown_blocks).strip() + "\n"

        base_name = Path(safe_filename).stem
        output_filename = f"{base_name}{suffix}.md"
        output_path = os.path.join(tmp_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(markdown_content)

        is_output_valid, output_error = validate_output_file(
            output_path,
            min_size=10,
            context=context,
        )
        if not is_output_valid:
            raise ConversionError(
                output_error or "Output file is invalid", context=context
            )

        logger.info(
            "PDF to Markdown conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
                "pages": len(page_markdown_blocks),
            },
        )
        return input_path, output_path

    except (StorageError, InvalidPDFError, ConversionError):
        raise
    except Exception as error:  # noqa: BLE001
        logger.exception(
            "PDF to Markdown conversion failed",
            extra={**context, "error": str(error)},
        )
        raise ConversionError(
            f"Failed to convert PDF to Markdown: {error}",
            context=context,
        ) from error
