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
                        try:
                            for table in plumber_doc.pages[page_index].find_tables():
                                markdown_table = _render_markdown_table(table.extract())
                                if markdown_table:
                                    x0, y0, x1, y1 = tuple(float(v) for v in table.bbox)
                                    table_bboxes.append((x0, y0, x1, y1))
                                    table_items.append(
                                        {
                                            "type": "table",
                                            "x": x0,
                                            "y": y0,
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

                            if heading_level:
                                markdown_line = f"{'#' * heading_level} {line_text}"
                            else:
                                markdown_line = line_text

                            text_items.append(
                                {
                                    "type": "text",
                                    "x": bbox_tuple[0],
                                    "y": bbox_tuple[1],
                                    "text": markdown_line,
                                }
                            )

                    merged_items = sorted(
                        [*text_items, *table_items],
                        key=lambda item: (float(item["y"]), float(item["x"])),
                    )

                    page_lines: list[str] = []
                    for item in merged_items:
                        item_text = str(item["text"]).strip()
                        if not item_text:
                            continue

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
