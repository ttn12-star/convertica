"""Utilities for visual PDF comparison and change reporting."""

from __future__ import annotations

import difflib
import json
import os
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import fitz
import numpy as np
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from PIL import Image
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)


def _render_page_rgb_array(page: fitz.Page, zoom: float = 1.6) -> np.ndarray:
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height,
        pixmap.width,
        pixmap.n,
    )
    if pixmap.n == 4:
        array = array[:, :, :3]
    return np.ascontiguousarray(array)


def _pad_to_same_canvas(
    first: np.ndarray,
    second: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    target_height = max(first.shape[0], second.shape[0])
    target_width = max(first.shape[1], second.shape[1])

    canvas_first = np.full((target_height, target_width, 3), 255, dtype=np.uint8)
    canvas_second = np.full((target_height, target_width, 3), 255, dtype=np.uint8)

    canvas_first[: first.shape[0], : first.shape[1], : first.shape[2]] = first[:, :, :3]
    canvas_second[: second.shape[0], : second.shape[1], : second.shape[2]] = second[
        :, :, :3
    ]

    return canvas_first, canvas_second


def _word_diff_stats(old_text: str, new_text: str) -> tuple[int, int, float]:
    old_words = old_text.split()
    new_words = new_text.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words)

    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            removed += i2 - i1
            added += j2 - j1

    similarity = round(matcher.ratio() * 100, 2)
    return added, removed, similarity


def compare_pdf_files(
    uploaded_file_1: UploadedFile,
    uploaded_file_2: UploadedFile,
    diff_threshold: int = 32,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Generate visual and textual diff package for two PDF files."""
    context = {
        "function": "compare_pdf_files",
        "base_filename": os.path.basename(uploaded_file_1.name),
        "compare_filename": os.path.basename(uploaded_file_2.name),
        "base_size": uploaded_file_1.size,
        "compare_size": uploaded_file_2.size,
        "diff_threshold": diff_threshold,
    }

    logger.info("Starting PDF comparison", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="compare_pdf_")
    base_path = None
    compare_path = None
    output_path = None

    try:
        required_mb = max(
            200,
            int(((uploaded_file_1.size + uploaded_file_2.size) * 12) / (1024 * 1024)),
        )
        has_space, disk_error = check_disk_space(tmp_dir, required_mb=required_mb)
        if not has_space:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        base_name = sanitize_filename(get_valid_filename(uploaded_file_1.name))
        compare_name = sanitize_filename(get_valid_filename(uploaded_file_2.name))
        base_path = os.path.join(tmp_dir, base_name)
        compare_path = os.path.join(tmp_dir, compare_name)

        with open(base_path, "wb") as file_obj:
            for chunk in uploaded_file_1.chunks():
                file_obj.write(chunk)
        with open(compare_path, "wb") as file_obj:
            for chunk in uploaded_file_2.chunks():
                file_obj.write(chunk)

        base_valid, base_error = validate_pdf_file(base_path, context)
        if not base_valid:
            raise InvalidPDFError(base_error or "First PDF is invalid", context=context)

        compare_valid, compare_error = validate_pdf_file(compare_path, context)
        if not compare_valid:
            raise InvalidPDFError(
                compare_error or "Second PDF is invalid", context=context
            )

        with fitz.open(base_path) as base_document, fitz.open(
            compare_path
        ) as compare_document:
            max_pages = max(len(base_document), len(compare_document))
            assets_dir = os.path.join(tmp_dir, "comparison_assets")
            os.makedirs(assets_dir, exist_ok=True)

            page_reports: list[dict[str, object]] = []
            total_changed_pixels = 0
            total_pixels = 0

            for page_index in range(max_pages):
                page_number = page_index + 1
                base_page = (
                    base_document[page_index]
                    if page_index < len(base_document)
                    else None
                )
                compare_page = (
                    compare_document[page_index]
                    if page_index < len(compare_document)
                    else None
                )

                if base_page is None and compare_page is not None:
                    compare_image = _render_page_rgb_array(compare_page)
                    base_image = np.full_like(compare_image, 255)
                    page_status = "added_in_second_pdf"
                elif compare_page is None and base_page is not None:
                    base_image = _render_page_rgb_array(base_page)
                    compare_image = np.full_like(base_image, 255)
                    page_status = "missing_in_second_pdf"
                else:
                    base_image = _render_page_rgb_array(base_page)
                    compare_image = _render_page_rgb_array(compare_page)
                    page_status = "present_in_both"

                base_canvas, compare_canvas = _pad_to_same_canvas(
                    base_image, compare_image
                )

                diff_mean = np.abs(
                    base_canvas.astype(np.int16) - compare_canvas.astype(np.int16)
                )
                diff_gray = diff_mean.mean(axis=2)
                change_mask = diff_gray >= diff_threshold

                changed_pixels = int(np.count_nonzero(change_mask))
                page_pixels = int(change_mask.size)
                change_percent = round((changed_pixels / max(page_pixels, 1)) * 100, 2)

                total_changed_pixels += changed_pixels
                total_pixels += page_pixels

                highlight_overlay = compare_canvas.copy()
                highlight_overlay[change_mask] = [255, 0, 0]
                blended = np.clip(
                    (compare_canvas.astype(np.float32) * 0.6)
                    + (highlight_overlay.astype(np.float32) * 0.4),
                    0,
                    255,
                ).astype(np.uint8)

                old_image_name = f"page_{page_number:03d}_base.png"
                new_image_name = f"page_{page_number:03d}_compare.png"
                diff_image_name = f"page_{page_number:03d}_diff.png"

                Image.fromarray(base_canvas).save(
                    os.path.join(assets_dir, old_image_name)
                )
                Image.fromarray(compare_canvas).save(
                    os.path.join(assets_dir, new_image_name)
                )
                Image.fromarray(blended).save(os.path.join(assets_dir, diff_image_name))

                old_text = (
                    base_page.get_text("text").strip() if base_page is not None else ""
                )
                new_text = (
                    compare_page.get_text("text").strip()
                    if compare_page is not None
                    else ""
                )
                words_added, words_removed, similarity = _word_diff_stats(
                    old_text, new_text
                )

                page_reports.append(
                    {
                        "page": page_number,
                        "status": page_status,
                        "changed_pixels": changed_pixels,
                        "total_pixels": page_pixels,
                        "change_percent": change_percent,
                        "words_added": words_added,
                        "words_removed": words_removed,
                        "text_similarity_percent": similarity,
                        "diff_image": f"comparison_assets/{diff_image_name}",
                        "base_image": f"comparison_assets/{old_image_name}",
                        "compare_image": f"comparison_assets/{new_image_name}",
                    }
                )

        overall_change = round((total_changed_pixels / max(total_pixels, 1)) * 100, 2)
        generated_at = datetime.now(UTC).isoformat()

        report_markdown_lines = [
            "# PDF Comparison Report",
            "",
            f"- Generated at (UTC): `{generated_at}`",
            f"- Base file: `{base_name}`",
            f"- Compared file: `{compare_name}`",
            f"- Pages analyzed: `{max_pages}`",
            f"- Overall visual change: `{overall_change}%`",
            "",
            "## Page Summary",
            "",
            "| Page | Status | Visual Change % | Words Added | Words Removed | Text Similarity % |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]

        for page_report in page_reports:
            report_markdown_lines.append(
                "| "
                f"{page_report['page']} | "
                f"{page_report['status']} | "
                f"{page_report['change_percent']} | "
                f"{page_report['words_added']} | "
                f"{page_report['words_removed']} | "
                f"{page_report['text_similarity_percent']} |"
            )

        report_markdown_lines.extend(["", "## Visual Assets", ""])
        for page_report in page_reports:
            report_markdown_lines.append(
                f"- Page {page_report['page']}: `{page_report['diff_image']}`"
            )

        report_markdown = "\n".join(report_markdown_lines).strip() + "\n"

        report_json = {
            "generated_at_utc": generated_at,
            "base_file": base_name,
            "compared_file": compare_name,
            "pages_analyzed": max_pages,
            "overall_visual_change_percent": overall_change,
            "page_reports": page_reports,
        }

        report_md_path = os.path.join(tmp_dir, "report.md")
        report_json_path = os.path.join(tmp_dir, "report.json")
        with open(report_md_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(report_markdown)
        with open(report_json_path, "w", encoding="utf-8") as file_obj:
            json.dump(report_json, file_obj, ensure_ascii=False, indent=2)

        output_filename = (
            f"{Path(base_name).stem}_vs_{Path(compare_name).stem}{suffix}.zip"
        )
        output_filename = sanitize_filename(output_filename)
        output_path = os.path.join(tmp_dir, output_filename)

        with zipfile.ZipFile(
            output_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.write(report_md_path, arcname="report.md")
            archive.write(report_json_path, arcname="report.json")

            for asset_name in sorted(os.listdir(assets_dir)):
                asset_path = os.path.join(assets_dir, asset_name)
                archive.write(asset_path, arcname=f"comparison_assets/{asset_name}")

        is_output_valid, output_error = validate_output_file(
            output_path,
            min_size=100,
            context=context,
        )
        if not is_output_valid:
            raise ConversionError(
                output_error or "Output archive is invalid", context=context
            )

        logger.info(
            "PDF comparison completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": os.path.getsize(output_path),
                "pages": max_pages,
                "overall_change_percent": overall_change,
            },
        )

        return base_path, output_path

    except (StorageError, InvalidPDFError, ConversionError):
        raise
    except Exception as error:  # noqa: BLE001
        logger.exception(
            "PDF comparison failed",
            extra={**context, "error": str(error)},
        )
        raise ConversionError(
            f"Failed to compare PDF files: {error}",
            context=context,
        ) from error
