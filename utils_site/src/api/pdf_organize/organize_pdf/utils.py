# utils.py
import os
import tempfile
from typing import Tuple

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


def organize_pdf(
    uploaded_file: UploadedFile,
    operation: str = 'reorder',
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """General PDF organization function.
    
    Args:
        uploaded_file: PDF file
        operation: Type of operation (placeholder for future operations)
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "organize_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "operation": operation,
    }
    
    try:
        tmp_dir = tempfile.mkdtemp(prefix="organize_pdf_")
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
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as err:
            raise StorageError(f"Failed to write PDF: {err}", context=context) from err
        
        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower():
                raise EncryptedPDFError(validation_error or "PDF is password-protected", context=context)
            raise InvalidPDFError(validation_error or "Invalid PDF file", context=context)
        
        # For now, just copy the PDF (placeholder for future operations)
        try:
            logger.info("Organizing PDF", extra={**context, "event": "organize_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Organization completed", extra={**context, "event": "organize_complete"})
            
        except Exception as e:
            error_context = {**context, "error_type": type(e).__name__, "error_message": str(e)}
            logger.error("Failed to organize PDF", extra={**error_context, "event": "organize_error"}, exc_info=True)
            raise ConversionError(f"Failed to organize PDF: {e}", context=error_context) from e
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            raise ConversionError(validation_error or "Output PDF is invalid", context=context)
        
        output_size = os.path.getsize(output_path)
        logger.info("PDF organized successfully", extra={
            **context, "event": "organize_success",
            "output_size": output_size, "output_size_mb": round(output_size / (1024 * 1024), 2),
        })
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception("Unexpected error", extra={**context, "event": "unexpected_error", "error_type": type(e).__name__})
        raise ConversionError(f"Unexpected error: {e}", context={**context, "error_type": type(e).__name__}) from e

