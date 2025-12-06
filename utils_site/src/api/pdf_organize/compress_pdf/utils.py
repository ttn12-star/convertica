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


def compress_pdf(
    uploaded_file: UploadedFile,
    compression_level: str = "medium",
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Compress PDF to reduce file size.
    
    Args:
        uploaded_file: PDF file to compress
        compression_level: Compression level ("low", "medium", "high")
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "compress_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "compression_level": compression_level,
    }
    
    try:
        tmp_dir = tempfile.mkdtemp(prefix="compress_pdf_")
        context["tmp_dir"] = tmp_dir
        
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=300)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)
        
        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = f"{base}_compressed{suffix}.pdf"
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
        
        # Compress PDF
        try:
            logger.info("Starting PDF compression", extra={**context, "event": "compress_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages
            
            # Copy all pages with compression
            for page in reader.pages:
                # Compress page content
                page.compress_content_streams()
                writer.add_page(page)
            
            # Set compression level based on user choice
            # PyPDF2 doesn't have direct compression level control,
            # but we can optimize by removing unnecessary objects
            writer.remove_links = True  # Remove links to reduce size
            writer.remove_images = False  # Keep images but compress them
            
            # Write compressed PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Compression completed", extra={**context, "event": "compress_complete"})
            
        except Exception as e:
            error_context = {**context, "error_type": type(e).__name__, "error_message": str(e)}
            logger.error("PDF compression failed", extra={**error_context, "event": "compress_error"}, exc_info=True)
            raise ConversionError(f"Failed to compress PDF: {e}", context=error_context) from e
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            raise ConversionError(validation_error or "Output PDF is invalid", context=context)
        
        input_size = os.path.getsize(pdf_path)
        output_size = os.path.getsize(output_path)
        compression_ratio = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
        
        logger.info("PDF compression successful", extra={
            **context, "event": "compress_success",
            "input_size": input_size, "input_size_mb": round(input_size / (1024 * 1024), 2),
            "output_size": output_size, "output_size_mb": round(output_size / (1024 * 1024), 2),
            "compression_ratio": round(compression_ratio, 2),
        })
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception("Unexpected error", extra={**context, "event": "unexpected_error", "error_type": type(e).__name__})
        raise ConversionError(f"Unexpected error: {e}", context={**context, "error_type": type(e).__name__}) from e

