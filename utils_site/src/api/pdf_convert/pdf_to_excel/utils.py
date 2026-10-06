import gc
import os
import re
import tempfile
from collections.abc import Callable

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


# Unambiguous numbers only. Text stays text when the number could be read two
# ways or is not really a quantity:
#   "1.200", "1,234": one separator + 3 digits = thousands in de/ru/pl/es
#   "007", 12+ digit integers: codes, IDs, phone numbers
#   "1,5", "1 234,5": decimal comma
# "1,234,567" and "1,234.56" are unambiguous (several groups, or a dot after).
_PLAIN_NUMBER = re.compile(r"-?(0|[1-9]\d{0,10})(\.(\d{1,2}|\d{4,}))?")
_THOUSANDS_NUMBER = re.compile(r"-?[1-9]\d{0,2}((,\d{3}){2,4}(\.\d+)?|,\d{3}\.\d+)")


def _numeric_or_text(column):
    """(column as numbers, decimals to display) if every cell is one, else (column, None).

    pdfplumber returns every cell as text, so Excel showed "number stored as
    text" and SUM() ignored the column. The decimals keep "12.30" from
    displaying as 12.3.
    """
    values = [str(v).strip() for v in column if v is not None and str(v).strip()]
    if not values or not all(
        _PLAIN_NUMBER.fullmatch(v) or _THOUSANDS_NUMBER.fullmatch(v) for v in values
    ):
        return column, None
    decimals = max(len(v.partition(".")[2]) for v in values)
    numbers = column.map(
        lambda v: (
            float(str(v).strip().replace(",", ""))
            if v is not None and str(v).strip()
            else None
        )
    ).map(lambda f: int(f) if f is not None and f.is_integer() and not decimals else f)
    return numbers, decimals


def convert_pdf_to_excel(
    uploaded_file: UploadedFile,
    pages: str = "all",
    suffix: str = "_convertica",
    check_cancelled: Callable[[], None] | None = None,
    **kwargs,
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

    # Check cancellation before starting
    if callable(check_cancelled):
        check_cancelled()

    try:
        with open(pdf_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
    except OSError as err:
        raise StorageError(f"Failed to write PDF: {err}", context=context) from err

    # Check cancellation after file write
    if callable(check_cancelled):
        check_cancelled()

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
                # Check cancellation at the start of each page
                if callable(check_cancelled):
                    check_cancelled()

                if idx < 0 or idx >= total_pages:
                    continue

                page = pdf.pages[idx]
                # pdfplumber caches every parsed page on the Page object until the
                # document closes: ~900 MB on a 200-page file in a celery child
                # that shares 2G with two neighbours. Drop it as we go.
                try:
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
                        lines = [
                            _normalize_text_line(line) for line in text.splitlines()
                        ]
                        lines = [l for l in lines if l]
                        if lines:
                            text_pages.append({"page": idx + 1, "lines": lines})
                            continue

                    image_pages.append(idx)
                finally:
                    page.flush_cache()
                    page.close()

        used_sheets = set()
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
                decimal_columns = {}
                for col in df.columns:
                    df[col], decimals = _numeric_or_text(df[col])
                    if decimals:
                        decimal_columns[col] = decimals

                # A second table from the same page used to be written into
                # the same "Page N" sheet from A1, overwriting the first.
                sheet_name = f"Page {page_num}"
                copy = 2
                while sheet_name in used_sheets:
                    sheet_name = f"Page {page_num} ({copy})"
                    copy += 1
                used_sheets.add(sheet_name)
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                sheet = writer.sheets[sheet_name[:31]]
                for col, decimals in decimal_columns.items():
                    col_idx = list(df.columns).index(col) + 1
                    for (cell,) in sheet.iter_rows(
                        min_row=2, min_col=col_idx, max_col=col_idx
                    ):
                        cell.number_format = "0." + "0" * decimals

            for item in text_pages:
                page_num = item["page"]
                df = pd.DataFrame(item["lines"], columns=["Text"])
                sheet_name = f"Page {page_num} Text"
                sheet_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            if image_pages:
                wb = writer.book

                for idx in image_pages:
                    # Check cancellation before processing each image page
                    if callable(check_cancelled):
                        check_cancelled()

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
