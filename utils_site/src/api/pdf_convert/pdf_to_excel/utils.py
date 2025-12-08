# utils.py
import os
import tempfile
from typing import Tuple

import pandas as pd
from django.core.files.uploadedfile import UploadedFile
from src.exceptions import (
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
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def convert_pdf_to_excel(
    uploaded_file: UploadedFile, pages: str = "all", suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Convert PDF to Excel by extracting tables.

    Args:
        uploaded_file: PDF file to convert
        pages: Pages to extract (comma-separated, ranges, or "all")
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "pdf_to_excel",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "pages": pages,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="pdf_to_excel_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=500)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}{suffix}.xlsx"
        output_path = os.path.join(tmp_dir, output_name)

        context.update({"pdf_path": pdf_path, "output_path": output_path})

        # Write uploaded file
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as io_err:
            raise StorageError(
                f"Failed to write PDF: {io_err}", context=context
            ) from io_err

        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower():
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected", context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Repair PDF to handle potentially corrupted files
        pdf_path = repair_pdf(pdf_path)

        # Convert PDF to Excel
        try:
            logger.info(
                "Starting PDF to Excel conversion",
                extra={**context, "event": "conversion_start"},
            )

            import pdfplumber
            from openpyxl.drawing.image import Image as OpenpyxlImage
            from pdf2image import convert_from_bytes, convert_from_path

            # Parse pages
            page_numbers = None
            if pages and pages.lower() != "all":
                page_list = []
                for part in pages.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-", 1)
                        try:
                            start_num = int(start.strip())
                            end_num = int(end.strip())
                            page_list.extend(range(start_num, end_num + 1))
                        except ValueError:
                            logger.warning(f"Invalid page range: {part}", extra=context)
                            continue
                    else:
                        try:
                            page_list.append(int(part.strip()))
                        except ValueError:
                            logger.warning(
                                f"Invalid page number: {part}", extra=context
                            )
                            continue
                page_numbers = [p - 1 for p in page_list]  # Convert to 0-indexed

            # Extract tables from PDF
            all_tables = []
            pages_with_images = []  # Pages that need image fallback

            try:
                with pdfplumber.open(pdf_path) as pdf:
                    total_pages = len(pdf.pages)
                    context["total_pages"] = total_pages

                    pages_to_process = (
                        page_numbers if page_numbers else range(total_pages)
                    )

                    for page_num in pages_to_process:
                        if page_num < 0 or page_num >= total_pages:
                            logger.warning(
                                f"Skipping invalid page number: {page_num + 1}",
                                extra={**context, "page_num": page_num + 1},
                            )
                            continue

                        try:
                            page = pdf.pages[page_num]

                            # Try multiple extraction strategies for better table detection
                            tables = None

                            # Strategy 1: Default extraction
                            try:
                                tables = page.extract_tables()
                            except Exception as e:
                                logger.debug(
                                    f"Default table extraction failed for page {page_num + 1}: {e}",
                                    extra={**context, "page": page_num + 1},
                                )

                            # Strategy 2: If no tables found, try with explicit table settings
                            if not tables or len(tables) == 0:
                                try:
                                    # Try with more aggressive table detection settings
                                    tables = page.extract_tables(
                                        table_settings={
                                            "vertical_strategy": "lines_strict",
                                            "horizontal_strategy": "lines_strict",
                                            "explicit_vertical_lines": [],
                                            "explicit_horizontal_lines": [],
                                            "snap_tolerance": 3,
                                            "join_tolerance": 3,
                                            "edge_tolerance": 3,
                                            "min_words_vertical": 1,
                                            "min_words_horizontal": 1,
                                        }
                                    )
                                except Exception as e:
                                    logger.debug(
                                        f"Aggressive table extraction failed for page {page_num + 1}: {e}",
                                        extra={**context, "page": page_num + 1},
                                    )

                            # Strategy 3: Try with text-based detection
                            if not tables or len(tables) == 0:
                                try:
                                    tables = page.extract_tables(
                                        table_settings={
                                            "vertical_strategy": "text",
                                            "horizontal_strategy": "text",
                                        }
                                    )
                                except Exception as e:
                                    logger.debug(
                                        f"Text-based table extraction failed for page {page_num + 1}: {e}",
                                        extra={**context, "page": page_num + 1},
                                    )

                            page_has_valid_tables = False

                            if tables and len(tables) > 0:
                                logger.debug(
                                    f"Found {len(tables)} table(s) on page {page_num + 1}",
                                    extra={
                                        **context,
                                        "page": page_num + 1,
                                        "tables_count": len(tables),
                                    },
                                )

                                for table in tables:
                                    # Validate table structure
                                    if not table or len(table) == 0:
                                        continue

                                    # Check if table has meaningful data (not all empty)
                                    has_data = False
                                    non_empty_cells = 0
                                    for row in table:
                                        if row:
                                            for cell in row:
                                                if (
                                                    cell is not None
                                                    and str(cell).strip()
                                                ):
                                                    has_data = True
                                                    non_empty_cells += 1

                                    if (
                                        has_data and non_empty_cells >= 2
                                    ):  # At least 2 non-empty cells
                                        all_tables.append(
                                            {"page": page_num + 1, "table": table}
                                        )
                                        page_has_valid_tables = True
                                        logger.debug(
                                            f"Valid table found on page {page_num + 1} with {non_empty_cells} non-empty cells",
                                            extra={
                                                **context,
                                                "page": page_num + 1,
                                                "cells": non_empty_cells,
                                            },
                                        )
                                    else:
                                        logger.debug(
                                            (
                                                "Empty or insufficient table found on "
                                                "page %d (only %d non-empty cells)"
                                            ),
                                            page_num + 1,
                                            non_empty_cells,
                                            extra={
                                                **context,
                                                "page": page_num + 1,
                                                "cells": non_empty_cells,
                                            },
                                        )
                            else:
                                logger.debug(
                                    f"No tables found on page {page_num + 1}",
                                    extra={**context, "page": page_num + 1},
                                )

                            # If no valid tables found on this page, mark for image fallback
                            if not page_has_valid_tables:
                                pages_with_images.append(page_num + 1)

                        except Exception as page_err:
                            logger.warning(
                                f"Error processing page {page_num + 1}: {page_err}",
                                extra={
                                    **context,
                                    "page": page_num + 1,
                                    "error": str(page_err),
                                },
                                exc_info=True,
                            )
                            # Mark page for image fallback if table extraction fails
                            pages_with_images.append(page_num + 1)

            except Exception as pdf_err:
                logger.error(
                    f"Error opening PDF with pdfplumber: {pdf_err}",
                    extra={**context, "error": str(pdf_err)},
                    exc_info=True,
                )
                # If pdfplumber fails completely, try image fallback for all pages
                if page_numbers:
                    pages_with_images = [p + 1 for p in page_numbers]
                else:
                    # Need to get total pages first
                    try:
                        from PyPDF2 import PdfReader

                        reader = PdfReader(pdf_path)
                        total_pages = len(reader.pages)
                        pages_with_images = list(range(1, total_pages + 1))
                    except Exception:
                        raise ConversionError(
                            f"Failed to process PDF: {pdf_err}", context=context
                        ) from pdf_err

            # Create Excel file
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                # Add tables to Excel
                if all_tables:
                    for idx, table_data in enumerate(all_tables):
                        page_num = table_data["page"]
                        table = table_data["table"]

                        try:
                            # Convert table to DataFrame
                            # Handle empty or malformed tables
                            if not table or len(table) == 0:
                                continue

                            # Use first row as headers if available
                            if len(table) > 1:
                                headers = table[0]
                                data_rows = table[1:]
                            else:
                                headers = None
                                data_rows = table

                            # Clean headers and data
                            if headers:
                                headers = [
                                    str(h).strip() if h is not None else f"Column {i+1}"
                                    for i, h in enumerate(headers)
                                ]

                            # Create DataFrame
                            df = pd.DataFrame(data_rows, columns=headers)

                            # Clean DataFrame (remove completely empty rows/columns)
                            df = df.dropna(how="all").dropna(axis=1, how="all")

                            # Skip if DataFrame is empty after cleaning
                            if df.empty:
                                logger.warning(
                                    f"Table on page {page_num} is empty after cleaning",
                                    extra={**context, "page": page_num},
                                )
                                continue

                            # Generate sheet name
                            sheet_name = f"Page {page_num}"
                            if len(all_tables) > 1:
                                sheet_name = f"Page {page_num} T{idx + 1}"

                            # Limit sheet name length (Excel limit is 31 characters)
                            if len(sheet_name) > 31:
                                sheet_name = sheet_name[:31]

                            # Ensure unique sheet names
                            base_sheet_name = sheet_name
                            counter = 1
                            while sheet_name in [
                                ws.title
                                for ws in writer.book.worksheets
                                if hasattr(writer, "book")
                            ]:
                                sheet_name = f"{base_sheet_name[:28]}_{counter}"
                                counter += 1

                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            logger.debug(
                                f"Added table from page {page_num} to Excel",
                                extra={**context, "page": page_num, "rows": len(df)},
                            )

                        except Exception as table_err:
                            logger.warning(
                                f"Failed to add table from page {page_num}: {table_err}",
                                extra={
                                    **context,
                                    "page": page_num,
                                    "error": str(table_err),
                                },
                                exc_info=True,
                            )
                            # Mark page for image fallback
                            if page_num not in pages_with_images:
                                pages_with_images.append(page_num)

                # If there are pages that need image fallback (no tables found on those pages)
                if pages_with_images:
                    # Convert pages to images and add to Excel
                    try:
                        logger.info(
                            f"Converting {len(pages_with_images)} page(s) to images as fallback",
                            extra={
                                **context,
                                "pages_count": len(pages_with_images),
                                "pages": pages_with_images,
                            },
                        )

                        # Read PDF for image conversion
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()

                        # Convert pages to images
                        try:
                            images = convert_from_bytes(pdf_bytes, dpi=150, fmt="jpeg")
                        except Exception:
                            images = convert_from_path(pdf_path, dpi=150, fmt="jpeg")

                        # Add images to Excel
                        workbook = writer.book

                        for page_num in pages_with_images:
                            if page_num < 1 or page_num > len(images):
                                continue

                            try:
                                # Get image for this page (0-indexed)
                                img = images[page_num - 1]

                                # Save image temporarily
                                img_path = os.path.join(
                                    tmp_dir, f"page_{page_num}_image.jpg"
                                )
                                img.save(img_path, "JPEG", quality=85, optimize=True)

                                # Create a new sheet for the image
                                sheet_name = f"Page {page_num} Image"
                                if len(sheet_name) > 31:
                                    sheet_name = sheet_name[:31]

                                # Ensure unique sheet name
                                base_sheet_name = sheet_name
                                counter = 1
                                existing_names = [
                                    ws.title for ws in workbook.worksheets
                                ]
                                while sheet_name in existing_names:
                                    sheet_name = f"{base_sheet_name[:28]}_{counter}"
                                    counter += 1

                                # Create worksheet
                                worksheet = workbook.create_sheet(title=sheet_name)

                                # Add image to worksheet
                                img_obj = OpenpyxlImage(img_path)

                                # Resize image to fit within Excel cell limits (max width ~1000px, height ~800px)
                                max_width = 1000
                                max_height = 800

                                img_width, img_height = img.size
                                scale = min(
                                    max_width / img_width, max_height / img_height, 1.0
                                )

                                img_obj.width = int(img_width * scale)
                                img_obj.height = int(img_height * scale)

                                # Add image at cell A1
                                worksheet.add_image(img_obj, "A1")

                                # Adjust column width to fit image
                                worksheet.column_dimensions["A"].width = min(
                                    img_obj.width / 7, 100
                                )  # Excel column width units

                                logger.debug(
                                    f"Added image from page {page_num} to Excel",
                                    extra={**context, "page": page_num},
                                )

                            except Exception as img_err:
                                logger.warning(
                                    f"Failed to add image from page {page_num}: {img_err}",
                                    extra={
                                        **context,
                                        "page": page_num,
                                        "error": str(img_err),
                                    },
                                    exc_info=True,
                                )
                                continue

                        # If no tables were found at all, add a note
                        if not all_tables:
                            try:
                                note_sheet = workbook.create_sheet(
                                    title="Note", index=0
                                )
                                note_sheet["A1"] = "No tables found in PDF"
                                note_sheet["A2"] = (
                                    "Pages have been converted to images instead."
                                )
                                note_sheet["A3"] = (
                                    "Please check the image sheets for page content."
                                )
                            except Exception:
                                pass

                    except ImportError as img_import_err:
                        logger.warning(
                            "pdf2image or openpyxl.image not available for image fallback",
                            extra={**context, "error": str(img_import_err)},
                        )
                        if not all_tables:
                            raise ConversionError(
                                "No tables found in PDF and image fallback is not available. "
                                "Please ensure the PDF contains extractable tables or install pdf2image for image conversion.",
                                context=context,
                            ) from img_import_err
                    except Exception as img_fallback_err:
                        logger.error(
                            f"Image fallback failed: {img_fallback_err}",
                            extra={**context, "error": str(img_fallback_err)},
                            exc_info=True,
                        )
                        if not all_tables:
                            raise ConversionError(
                                f"No tables found and image conversion failed: {img_fallback_err}",
                                context=context,
                            ) from img_fallback_err

            # Log conversion results
            conversion_summary = {
                "tables_found": len(all_tables),
                "images_added": len(pages_with_images),
                "total_sheets": len(all_tables) + len(pages_with_images),
            }
            logger.info(
                "PDF to Excel conversion completed",
                extra={**context, **conversion_summary, "event": "conversion_complete"},
            )

        except ImportError as import_err:
            missing_module = (
                str(import_err).split("'")[1] if "'" in str(import_err) else "unknown"
            )
            if "pdfplumber" in missing_module or "pdfplumber" in str(import_err):
                raise ConversionError(
                    "pdfplumber is required for PDF to Excel conversion. Please install it.",
                    context=context,
                ) from import_err
            else:
                raise ConversionError(
                    f"Required module not available: {missing_module}", context=context
                ) from import_err
        except Exception as conv_exc:
            error_context = {
                **context,
                "error_type": type(conv_exc).__name__,
                "error_message": str(conv_exc),
            }
            logger.error(
                "PDF to Excel conversion failed",
                extra={**error_context, "event": "conversion_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Failed to convert PDF to Excel: {conv_exc}", context=error_context
            ) from conv_exc

        # Validate output
        is_valid, validation_error = validate_output_file(
            output_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output Excel file is invalid", context=context
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

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
