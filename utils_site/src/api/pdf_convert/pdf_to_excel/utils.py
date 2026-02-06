import os
import re
import tempfile

import pandas as pd
from django.core.files.uploadedfile import UploadedFile

from ....exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)
from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from ...logging_utils import get_logger
from ...pdf_utils import execute_with_repair_fallback

logger = get_logger(__name__)


def _normalize_text_line(line: str) -> str:
    """
    Normalize text extracted from PDF:
    - replace tabs and multiple spaces with single space
    - trim
    """
    return re.sub(r"\s+", " ", line).strip()


def _is_real_table(table: list[list[str | None]]) -> bool:
    """
    Very strict table validation to avoid false positives.
    """
    if not table or len(table) < 2:
        return False

    non_empty_cells = 0
    max_cols = 0

    for row in table:
        if not row:
            continue
        max_cols = max(max_cols, len(row))
        for cell in row:
            if cell and str(cell).strip():
                non_empty_cells += 1

    return max_cols >= 2 and non_empty_cells >= 4


def convert_pdf_to_excel(
    uploaded_file: UploadedFile,
    pages: str = "all",
    suffix: str = "_convertica",
) -> tuple[str, str]:
    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_excel_")

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "pdf_to_excel",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "pages": pages,
        "tmp_dir": tmp_dir,
    }

    disk_check, disk_error = check_disk_space(tmp_dir, required_mb=500)
    if not disk_check:
        raise StorageError(disk_error or "Insufficient disk space", context=context)

    pdf_path = os.path.join(tmp_dir, safe_name)
    base_name = os.path.splitext(safe_name)[0]
    output_path = os.path.join(tmp_dir, f"{base_name}{suffix}.xlsx")

    context.update({"pdf_path": pdf_path, "output_path": output_path})

    try:
        with open(pdf_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
    except OSError as err:
        raise StorageError(f"Failed to write PDF: {err}", context=context) from err

    is_valid, validation_error = validate_pdf_file(pdf_path, context)
    if not is_valid:
        if validation_error and "password" in validation_error.lower():
            raise EncryptedPDFError(validation_error, context=context)
        raise InvalidPDFError(validation_error or "Invalid PDF", context=context)

    def _pdf_to_excel_operation(pdf_path_inner: str):
        import pdfplumber
        from openpyxl.drawing.image import Image as XLImage
        from pdf2image import convert_from_path

        page_indices = None
        if pages.lower() != "all":
            parsed = []
            for part in pages.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        start, end = map(int, part.split("-", 1))
                        parsed.extend(range(start - 1, end))
                    except ValueError:
                        continue
                else:
                    try:
                        parsed.append(int(part) - 1)
                    except ValueError:
                        continue
            page_indices = parsed

        tables = []
        text_pages = []
        image_pages = []

        with pdfplumber.open(pdf_path_inner) as pdf:
            total_pages = len(pdf.pages)
            context["total_pages"] = total_pages

            indices = page_indices if page_indices is not None else range(total_pages)

            for idx in indices:
                if idx < 0 or idx >= total_pages:
                    continue

                page = pdf.pages[idx]
                page_has_content = False

                extracted_tables = []
                try:
                    extracted_tables = page.extract_tables() or []
                except Exception:
                    extracted_tables = []

                for table in extracted_tables:
                    if _is_real_table(table):
                        tables.append({"page": idx + 1, "table": table})
                        page_has_content = True

                if page_has_content:
                    continue

                try:
                    text = page.extract_text()
                except Exception:
                    text = None

                if text:
                    lines = [_normalize_text_line(line) for line in text.splitlines()]
                    lines = [l for l in lines if l]
                    if lines:
                        text_pages.append({"page": idx + 1, "lines": lines})
                        continue

                image_pages.append(idx)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for i, item in enumerate(tables):
                table = item["table"]
                page_num = item["page"]

                headers = table[0] if len(table) > 1 else None
                rows = table[1:] if headers else table

                if headers:
                    headers = [
                        str(h).strip() if h else f"Column {i + 1}"
                        for i, h in enumerate(headers)
                    ]

                df = pd.DataFrame(rows, columns=headers)
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if df.empty:
                    continue

                sheet_name = f"Page {page_num}"
                sheet_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            for item in text_pages:
                page_num = item["page"]
                df = pd.DataFrame(item["lines"], columns=["Text"])
                sheet_name = f"Page {page_num} Text"
                sheet_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            if image_pages:
                import gc

                wb = writer.book

                for idx in image_pages:
                    # Convert one page at a time to avoid memory issues
                    # (instead of loading all pages into memory at once)
                    page_images = convert_from_path(
                        pdf_path_inner,
                        dpi=150,
                        first_page=idx + 1,
                        last_page=idx + 1,
                    )
                    if not page_images:
                        continue

                    img = page_images[0]
                    img_path = os.path.join(tmp_dir, f"page_{idx + 1}.jpg")
                    img.save(img_path, "JPEG", quality=85, optimize=True)

                    ws = wb.create_sheet(title=f"Page {idx + 1} Image"[:31])
                    xl_img = XLImage(img_path)

                    scale = min(1000 / img.width, 800 / img.height, 1.0)
                    xl_img.width = int(img.width * scale)
                    xl_img.height = int(img.height * scale)

                    ws.add_image(xl_img, "A1")
                    ws.column_dimensions["A"].width = min(xl_img.width / 7, 100)

                    # Clean up memory after each page
                    del img
                    del page_images
                    gc.collect()

        return output_path

    output_path = execute_with_repair_fallback(
        pdf_path,
        _pdf_to_excel_operation,
        context=context,
    )

    is_valid, validation_error = validate_output_file(
        output_path,
        min_size=1000,
        context=context,
    )
    if not is_valid:
        raise ConversionError(
            validation_error or "Invalid output Excel", context=context
        )

    output_size = os.path.getsize(output_path)
    logger.info(
        "PDF to Excel conversion successful",
        extra={
            **context,
            "event": "conversion_success",
            "output_size": output_size,
            "output_size_mb": round(output_size / (1024 * 1024), 2),
        },
    )

    return pdf_path, output_path
