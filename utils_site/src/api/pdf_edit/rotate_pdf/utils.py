# utils.py
import os
import tempfile
import re
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


def rotate_pdf(
    uploaded_file: UploadedFile,
    angle: int = 90,
    pages: str = "all",
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Rotate PDF pages by specified angle.
    
    Args:
        uploaded_file: PDF file to rotate
        angle: Rotation angle in degrees (90, 180, or 270)
        pages: Pages to rotate ("all", "1,3,5", or "1-5")
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
        
    Raises:
        ConversionError, StorageError, InvalidPDFError, EncryptedPDFError
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "rotate_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "angle": angle,
        "pages": pages,
    }
    
    try:
        # Validate angle
        if angle not in [90, 180, 270]:
            raise ConversionError(
                "Rotation angle must be 90, 180, or 270 degrees",
                context=context
            )
        
        # Check disk space
        tmp_dir = tempfile.mkdtemp(prefix="rotate_pdf_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(
                disk_error or "Insufficient disk space",
                context=context
            )
        
        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)
        
        context.update({
            "pdf_path": pdf_path,
            "output_path": output_path,
        })
        
        # Write uploaded file
        try:
            logger.debug("Writing PDF file to temporary location", extra={**context, "event": "file_write_start"})
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            logger.debug("File written successfully", extra={**context, "event": "file_write_success"})
        except (OSError, IOError) as err:
            logger.error(
                "Failed to write PDF file",
                extra={**context, "event": "file_write_error", "error": str(err)},
                exc_info=True
            )
            raise StorageError(
                f"Failed to write PDF file: {err}",
                context={**context, "error_type": type(err).__name__}
            ) from err
        
        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower() or "encrypted" in (validation_error or "").lower():
                raise EncryptedPDFError(
                    validation_error or "PDF is password-protected",
                    context=context
                )
            raise InvalidPDFError(
                validation_error or "Invalid PDF file",
                context=context
            )
        
        # Rotate PDF
        try:
            logger.info("Starting PDF rotation", extra={**context, "event": "rotation_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            pages_to_rotate = parse_pages(pages, total_pages)
            
            context["total_pages"] = total_pages
            context["pages_to_rotate"] = len(pages_to_rotate)
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                
                if page_num in pages_to_rotate:
                    # Rotate the page
                    page.rotate(angle)
                
                writer.add_page(page)
            
            # Write output PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Rotation completed", extra={**context, "event": "rotation_complete"})
            
        except Exception as rot_exc:
            error_context = {**context, "error_type": type(rot_exc).__name__, "error_message": str(rot_exc)}
            
            if "encrypted" in str(rot_exc).lower() or "password" in str(rot_exc).lower():
                logger.warning(
                    "PDF is encrypted/password protected",
                    extra={**error_context, "event": "encrypted_pdf_error"}
                )
                raise EncryptedPDFError(
                    "PDF is encrypted/password protected",
                    context=error_context
                ) from rot_exc
            
            logger.error(
                "PDF rotation failed",
                extra={**error_context, "event": "rotation_error"},
                exc_info=True
            )
            raise ConversionError(
                f"Rotation failed: {rot_exc}",
                context=error_context
            ) from rot_exc
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={**context, "validation_error": validation_error, "event": "output_validation_failed"}
            )
            raise ConversionError(
                validation_error or "Output PDF file is invalid",
                context=context
            )
        
        output_size = os.path.getsize(output_path)
        logger.info(
            "PDF rotation successful",
            extra={
                **context,
                "event": "rotation_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            }
        )
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during PDF rotation",
            extra={**context, "event": "unexpected_error", "error_type": type(e).__name__}
        )
        raise ConversionError(
            f"Unexpected error during rotation: {e}",
            context={**context, "error_type": type(e).__name__}
        ) from e

