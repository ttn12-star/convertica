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


def protect_pdf(
    uploaded_file: UploadedFile,
    password: str,
    user_password: str = None,
    owner_password: str = None,
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Protect PDF with password encryption.
    
    Args:
        uploaded_file: PDF file to protect
        password: Password for both user and owner (if user_password/owner_password not provided)
        user_password: User password (optional, uses password if not provided)
        owner_password: Owner password (optional, uses password if not provided)
        permissions: PDF permissions (bit flags), -1 for all permissions
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "protect_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
    }
    
    try:
        tmp_dir = tempfile.mkdtemp(prefix="protect_pdf_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)
        
        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}_protected{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)
        
        context.update({"pdf_path": pdf_path, "output_path": output_path})
        
        # Write uploaded file
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as io_err:
            raise StorageError(f"Failed to write PDF: {io_err}", context=context) from io_err
        
        # Validate PDF
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            if "password" in (validation_error or "").lower():
                raise EncryptedPDFError(validation_error or "PDF is already password-protected", context=context)
            raise InvalidPDFError(validation_error or "Invalid PDF file", context=context)
        
        # Determine passwords
        user_pwd = user_password if user_password else password
        owner_pwd = owner_password if owner_password else password
        
        # Protect PDF
        try:
            logger.info("Starting PDF protection", extra={**context, "event": "protect_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Copy metadata if available
            if reader.metadata:
                writer.add_metadata(reader.metadata)
            
            # Encrypt PDF
            writer.encrypt(
                user_password=user_pwd,
                owner_password=owner_pwd,
                use_128bit=True,  # Use 128-bit encryption (stronger)
            )
            
            # Write protected PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Protection completed", extra={**context, "event": "protect_complete"})
            
        except Exception as e:
            error_context = {**context, "error_type": type(e).__name__, "error_message": str(e)}
            logger.error("PDF protection failed", extra={**error_context, "event": "protect_error"}, exc_info=True)
            raise ConversionError(f"Failed to protect PDF: {e}", context=error_context) from e
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            raise ConversionError(validation_error or "Output PDF is invalid", context=context)
        
        output_size = os.path.getsize(output_path)
        logger.info("PDF protection successful", extra={
            **context, "event": "protect_success",
            "output_size": output_size, "output_size_mb": round(output_size / (1024 * 1024), 2),
        })
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception("Unexpected error", extra={**context, "event": "unexpected_error", "error_type": type(e).__name__})
        raise ConversionError(f"Unexpected error: {e}", context={**context, "error_type": type(e).__name__}) from e

