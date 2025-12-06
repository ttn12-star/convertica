# utils.py
import os
import tempfile
import math
from typing import Tuple, Optional

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from PIL import Image
from io import BytesIO
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


def add_watermark(
    uploaded_file: UploadedFile,
    watermark_text: str = "CONFIDENTIAL",
    watermark_file: Optional[UploadedFile] = None,
    position: str = 'diagonal',
    opacity: float = 0.3,
    font_size: int = 72,
    suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Add watermark to PDF.
    
    Args:
        uploaded_file: PDF file
        watermark_text: Text watermark
        watermark_file: Image file for watermark (optional)
        position: Position ('center' or 'diagonal')
        opacity: Opacity (0.1-1.0)
        font_size: Font size for text watermark
        suffix: Suffix for output filename
        
    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "add_watermark",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "position": position,
        "opacity": opacity,
        "has_image": watermark_file is not None,
    }
    
    try:
        tmp_dir = tempfile.mkdtemp(prefix="watermark_")
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
        
        # Add watermark
        try:
            logger.info("Adding watermark", extra={**context, "event": "watermark_start"})
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Create watermark overlay
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.setFillAlpha(opacity)
                
                if watermark_file:
                    # Image watermark
                    try:
                        watermark_file.seek(0)
                        img = Image.open(watermark_file)
                        img_width, img_height = img.size
                        
                        # Scale to fit page
                        scale = min(page_width / img_width, page_height / img_height) * 0.5
                        scaled_width = img_width * scale
                        scaled_height = img_height * scale
                        
                        # Center position
                        x = (page_width - scaled_width) / 2
                        y = (page_height - scaled_height) / 2
                        
                        # Save image to temp and draw
                        img_path = os.path.join(tmp_dir, f"watermark_{page_num}.png")
                        img.save(img_path)
                        can.drawImage(img_path, x, y, width=scaled_width, height=scaled_height, mask='auto')
                    except Exception as img_err:
                        logger.warning(f"Failed to use image watermark: {img_err}, using text", extra=context)
                        # Fallback to text
                        can.setFont("Helvetica-Bold", font_size)
                        can.rotate(45)
                        x = page_width / 2
                        y = page_height / 2
                        can.drawCentredString(x, y, watermark_text)
                else:
                    # Text watermark
                    can.setFont("Helvetica-Bold", font_size)
                    if position == 'diagonal':
                        can.rotate(45)
                        x = page_width / 2
                        y = page_height / 2
                        can.drawCentredString(x, y, watermark_text)
                    else:  # center
                        x = page_width / 2
                        y = page_height / 2
                        can.drawCentredString(x, y, watermark_text)
                
                can.save()
                
                # Merge watermark with page
                packet.seek(0)
                overlay = PdfReader(packet)
                overlay_page = overlay.pages[0]
                page.merge_page(overlay_page)
                writer.add_page(page)
            
            # Write output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logger.debug("Watermark added", extra={**context, "event": "watermark_complete"})
            
        except Exception as e:
            error_context = {**context, "error_type": type(e).__name__, "error_message": str(e)}
            logger.error("Failed to add watermark", extra={**error_context, "event": "watermark_error"}, exc_info=True)
            raise ConversionError(f"Failed to add watermark: {e}", context=error_context) from e
        
        # Validate output
        is_valid, validation_error = validate_output_file(output_path, min_size=1000, context=context)
        if not is_valid:
            raise ConversionError(validation_error or "Output PDF is invalid", context=context)
        
        output_size = os.path.getsize(output_path)
        logger.info("Watermark added successfully", extra={
            **context, "event": "watermark_success",
            "output_size": output_size, "output_size_mb": round(output_size / (1024 * 1024), 2),
        })
        
        return pdf_path, output_path
        
    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception("Unexpected error", extra={**context, "event": "unexpected_error", "error_type": type(e).__name__})
        raise ConversionError(f"Unexpected error: {e}", context={**context, "error_type": type(e).__name__}) from e

