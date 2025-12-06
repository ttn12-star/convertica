# utils.py
import os
import tempfile
from typing import Tuple, List, Optional

import os
import tempfile
from typing import Tuple, List, Optional

from PyPDF2 import PdfReader, PdfWriter
from django.core.files.uploadedfile import UploadedFile

from src.exceptions import ConversionError, StorageError, InvalidPDFError, EncryptedPDFError
from ...logging_utils import get_logger
from ...file_validation import (
    validate_pdf_file,
    check_disk_space,
    sanitize_filename,
    validate_output_file,
)

logger = get_logger(__name__)


def parse_pages(pages_str: str, total_pages: int) -> List[int]:
    """Parse page string into list of page indices (0-indexed).
    
    Args:
        pages_str: Page string like "all", "1,3,5", or "1-5"
        total_pages: Total number of pages in PDF
        
    Returns:
        List of 0-indexed page numbers
    """
    if pages_str.lower() == "all":
        return list(range(total_pages))
    
    page_indices = []
    parts = pages_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Range like "1-5"
            start, end = part.split('-', 1)
            try:
                start_idx = max(0, int(start.strip()) - 1)  # Convert to 0-indexed
                end_idx = min(total_pages, int(end.strip()))  # Keep 1-indexed for range
                page_indices.extend(range(start_idx, end_idx))
            except ValueError:
                logger.warning(f"Invalid page range: {part}")
        else:
            # Single page number
            try:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    page_indices.append(page_num - 1)  # Convert to 0-indexed
            except ValueError:
                logger.warning(f"Invalid page number: {part}")
    
    return sorted(set(page_indices))  # Remove duplicates and sort

logger = get_logger(__name__)


def crop_pdf(
    uploaded_file: UploadedFile,
    x: float = 0.0,
    y: float = 0.0,
    width: Optional[float] = None,
    height: Optional[float] = None,
    pages: str = "all",
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Crop PDF pages.
    
    Args:
        uploaded_file: PDF file
        x: X coordinate (left edge)
        y: Y coordinate (bottom edge)
        width: Width of crop box (None = use remaining width)
        height: Height of crop box (None = use remaining height)
        pages: Pages to crop
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "crop_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "pages": pages,
    }
    
    try:
        tmp_dir = tempfile.mkdtemp(prefix="crop_pdf_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)
        
        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)
        
        context.update({"pdf_path": pdf_path, "output_path": output_path})
        
        # Write uploaded file
        try:
            logger.debug("Writing PDF file", extra={**context, "event": "file_write_start"})
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as err:
            raise StorageError(f"Failed to write PDF: {err}", context={**context, "error_type": type(err).__name__}) from err
        
        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower() or "encrypted" in (validation_error or "").lower():
                raise EncryptedPDFError(validation_error or "PDF is password-protected", context=context)
            raise InvalidPDFError(validation_error or "Invalid PDF file", context=context)
        
        # Crop PDF
        try:
            logger.info("Cropping PDF", extra={**context, "event": "crop_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            pages_to_crop = parse_pages(pages, total_pages)
            
            context["total_pages"] = total_pages
            context["pages_to_crop"] = len(pages_to_crop)
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                
                if page_num in pages_to_crop:
                    # Get page dimensions
                    page_width = float(page.mediabox.width)
                    page_height = float(page.mediabox.height)
                    
                    # Calculate crop box
                    crop_width = width if width is not None else (page_width - x)
                    crop_height = height if height is not None else (page_height - y)
                    
                    # Ensure crop box is within page bounds
                    crop_x = max(0, min(x, page_width))
                    crop_y = max(0, min(y, page_height))
                    crop_width = min(crop_width, page_width - crop_x)
                    crop_height = min(crop_height, page_height - crop_y)
                    
                    # Set crop box (lower-left, upper-right)
                    page.mediabox.lower_left = (crop_x, crop_y)
                    page.mediabox.upper_right = (crop_x + crop_width, crop_y + crop_height)
                
                writer.add_page(page)
            
            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Crop completed", extra={**context, "event": "crop_complete"})
            
        except Exception as e:
            error_context = {**context, "error_type": type(e).__name__, "error_message": str(e)}
            logger.error("Failed to crop PDF", extra={**error_context, "event": "crop_error"}, exc_info=True)
            raise ConversionError(f"Failed to crop PDF: {e}", context=error_context) from e
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            raise ConversionError(validation_error or "Output PDF is invalid", context=context)
        
        output_size = os.path.getsize(output_path)
        logger.info("PDF cropped successfully", extra={
            **context, "event": "crop_success",
            "output_size": output_size, "output_size_mb": round(output_size / (1024 * 1024), 2),
        })
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception("Unexpected error", extra={**context, "event": "unexpected_error", "error_type": type(e).__name__})
        raise ConversionError(f"Unexpected error: {e}", context={**context, "error_type": type(e).__name__}) from e

