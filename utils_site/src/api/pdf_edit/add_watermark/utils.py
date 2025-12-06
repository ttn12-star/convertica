# utils.py
import os
import tempfile
import math
from typing import Tuple, Optional, List

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


def add_watermark(
    uploaded_file: UploadedFile,
    watermark_text: str = "CONFIDENTIAL",
    watermark_file: Optional[UploadedFile] = None,
    position: str = 'diagonal',
    x: Optional[float] = None,
    y: Optional[float] = None,
    color: str = "#000000",
    opacity: float = 0.3,
    font_size: int = 72,
    rotation: float = 0.0,
    scale: float = 1.0,
    pages: str = "all",
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
            logger.info("Adding watermark", extra={
                **context, 
                "event": "watermark_start",
                "watermark_text": watermark_text[:50] if watermark_text else None,
                "has_image": watermark_file is not None,
                "position": position,
                "x": x,
                "y": y,
                "color": color,
                "opacity": opacity,
                "font_size": font_size,
                "rotation": rotation,
                "scale": scale,
                "pages": pages
            })
            logger.debug(f"Watermark parameters received: text='{watermark_text}', file={watermark_file is not None}, "
                        f"position='{position}', x={x}, y={y}, color='{color}', opacity={opacity}, "
                        f"font_size={font_size}, rotation={rotation}, scale={scale}, pages='{pages}'", extra=context)
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            context["total_pages"] = total_pages
            
            # Parse pages to watermark
            pages_to_watermark = parse_pages(pages, total_pages)
            context["pages_to_watermark"] = len(pages_to_watermark)
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                
                # Skip if page is not in the list
                if page_num not in pages_to_watermark:
                    writer.add_page(page)
                    continue
                
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Create watermark overlay
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.setFillAlpha(opacity)
                
                # Parse color (hex to RGB)
                try:
                    color_hex = color.lstrip('#')
                    color_r = int(color_hex[0:2], 16) / 255.0
                    color_g = int(color_hex[2:4], 16) / 255.0
                    color_b = int(color_hex[4:6], 16) / 255.0
                    can.setFillColorRGB(color_r, color_g, color_b)
                    logger.debug(f"Page {page_num + 1}: Applied color RGB({color_r:.3f}, {color_g:.3f}, {color_b:.3f}) from {color}, opacity={opacity}", extra=context)
                except (ValueError, IndexError):
                    # Default to black if color parsing fails
                    can.setFillColorRGB(0, 0, 0)
                    logger.warning(f"Page {page_num + 1}: Failed to parse color '{color}', using black", extra=context)
                
                if watermark_file:
                    # Image watermark
                    try:
                        # Reset file pointer to beginning
                        watermark_file.seek(0)
                        img = Image.open(watermark_file)
                        
                        # Convert to RGB if necessary (for PNG with transparency, etc.)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            # Create a white background for transparent images
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        img_width, img_height = img.size
                        logger.debug(f"Image watermark loaded: {img_width}x{img_height}, mode: {img.mode}", extra=context)
                        
                        # Scale to fit page, then apply user scale
                        base_scale = min(page_width / img_width, page_height / img_height) * 0.5
                        scaled_width = img_width * base_scale * scale
                        scaled_height = img_height * base_scale * scale
                        
                        # Calculate position
                        # For images, coordinates (x, y) represent the center point
                        # Priority: if coordinates are provided, use them regardless of position parameter
                        if x is not None and y is not None:
                            # If coordinates are provided, use them regardless of position
                            watermark_center_x = x
                            watermark_center_y = y
                            logger.debug(f"Page {page_num + 1}: Using provided coordinates ({x:.2f}, {y:.2f}) for image watermark", extra=context)
                        elif position == 'center':
                            watermark_center_x = page_width / 2
                            watermark_center_y = page_height / 2
                            logger.debug(f"Page {page_num + 1}: Using center position for image watermark", extra=context)
                        else:  # diagonal (default) or custom without coordinates
                            watermark_center_x = page_width / 2
                            watermark_center_y = page_height / 2
                            logger.debug(f"Page {page_num + 1}: Using default center position for image watermark", extra=context)
                        
                        # Calculate bottom-left corner for drawImage (ReportLab uses bottom-left origin)
                        watermark_x = watermark_center_x - scaled_width / 2
                        watermark_y = watermark_center_y - scaled_height / 2
                        
                        # Save image to temp as PNG (ReportLab can handle PNG)
                        img_path = os.path.join(tmp_dir, f"watermark_{page_num}.png")
                        # Save as RGB PNG (ReportLab works best with RGB)
                        img.save(img_path, 'PNG')
                        logger.debug(f"Saved watermark image to {img_path}", extra=context)
                        
                        # Apply rotation and scale transformations
                        # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                        should_apply_diagonal = (position == 'diagonal' and rotation == 0 and 
                                                (x is None or y is None))
                        
                        if rotation != 0:
                            # Save state, apply rotation around center, draw, restore
                            can.saveState()
                            can.translate(watermark_center_x, watermark_center_y)
                            can.rotate(rotation)
                            can.translate(-watermark_center_x, -watermark_center_y)
                            can.drawImage(img_path, watermark_x, watermark_y, width=scaled_width, height=scaled_height, mask='auto')
                            can.restoreState()
                        elif should_apply_diagonal:
                            # Apply diagonal rotation only if no custom coordinates and rotation=0
                            can.saveState()
                            can.translate(watermark_center_x, watermark_center_y)
                            can.rotate(45)
                            can.translate(-watermark_center_x, -watermark_center_y)
                            can.drawImage(img_path, watermark_x, watermark_y, width=scaled_width, height=scaled_height, mask='auto')
                            can.restoreState()
                        else:
                            can.drawImage(img_path, watermark_x, watermark_y, width=scaled_width, height=scaled_height, mask='auto')
                    except Exception as img_err:
                        logger.warning(f"Failed to use image watermark: {img_err}, using text", extra=context)
                        # Fallback to text - use same logic as text watermark below
                        scaled_font_size = font_size * scale
                        can.setFont("Helvetica-Bold", scaled_font_size)
                        
                        # Calculate text position (center point)
                        if position == 'custom' and x is not None and y is not None:
                            watermark_x = x
                            watermark_y = y
                        else:
                            watermark_x = page_width / 2
                            watermark_y = page_height / 2
                        
                        # Apply rotation and draw text
                        # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                        should_apply_diagonal = (position == 'diagonal' and rotation == 0 and 
                                                (x is None or y is None))
                        
                        if rotation != 0:
                            can.saveState()
                            can.translate(watermark_x, watermark_y)
                            can.rotate(rotation)
                            can.translate(-watermark_x, -watermark_y)
                            can.drawCentredString(watermark_x, watermark_y, watermark_text)
                            can.restoreState()
                        elif should_apply_diagonal:
                            can.saveState()
                            can.translate(watermark_x, watermark_y)
                            can.rotate(45)
                            can.translate(-watermark_x, -watermark_y)
                            can.drawCentredString(watermark_x, watermark_y, watermark_text)
                            can.restoreState()
                        else:
                            can.drawCentredString(watermark_x, watermark_y, watermark_text)
                else:
                    # Text watermark
                    # Ensure watermark_text is not empty
                    if not watermark_text or not watermark_text.strip():
                        watermark_text = "CONFIDENTIAL"
                        logger.warning("Empty watermark_text, using default 'CONFIDENTIAL'", extra=context)
                    
                    # Apply scale to font size
                    scaled_font_size = font_size * scale
                    can.setFont("Helvetica-Bold", scaled_font_size)
                    
                    # Calculate text position
                    # For text, coordinates (x, y) represent the center point
                    if x is not None and y is not None:
                        # If coordinates are provided, use them regardless of position parameter
                        watermark_x = x
                        watermark_y = y
                        logger.debug(f"Page {page_num + 1}: Using custom coordinates ({watermark_x:.2f}, {watermark_y:.2f})", extra=context)
                    elif position == 'center':
                        watermark_x = page_width / 2
                        watermark_y = page_height / 2
                        logger.debug(f"Page {page_num + 1}: Using center position ({watermark_x:.2f}, {watermark_y:.2f})", extra=context)
                    else:  # diagonal (default) or custom without coordinates
                        watermark_x = page_width / 2
                        watermark_y = page_height / 2
                        logger.debug(f"Page {page_num + 1}: Using default center position ({watermark_x:.2f}, {watermark_y:.2f})", extra=context)
                    
                    # Apply rotation and scale, then draw text
                    # Text is drawn centered at (watermark_x, watermark_y)
                    # Only apply diagonal rotation if position='diagonal' AND rotation=0 AND no custom coordinates
                    should_apply_diagonal = (position == 'diagonal' and rotation == 0 and 
                                            (x is None or y is None))
                    
                    logger.debug(f"Page {page_num + 1} text watermark: text='{watermark_text}', "
                               f"font_size={scaled_font_size}, position='{position}', "
                               f"x={x}, y={y}, watermark_pos=({watermark_x:.2f}, {watermark_y:.2f}), "
                               f"rotation={rotation}, scale={scale}, should_apply_diagonal={should_apply_diagonal}, "
                               f"color={color}, opacity={opacity}", extra=context)
                    
                    if rotation != 0:
                        # Save state, apply rotation around text center, draw, restore
                        can.saveState()
                        can.translate(watermark_x, watermark_y)
                        can.rotate(rotation)
                        can.translate(-watermark_x, -watermark_y)
                        # Scale font size is already applied via scaled_font_size
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        can.restoreState()
                        logger.debug(f"Applied rotation {rotation} degrees to text watermark", extra=context)
                    elif should_apply_diagonal:
                        # Only diagonal rotation if no custom coordinates and no custom rotation
                        can.saveState()
                        can.translate(watermark_x, watermark_y)
                        can.rotate(45)
                        can.translate(-watermark_x, -watermark_y)
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        can.restoreState()
                        logger.debug("Applied diagonal rotation (45 degrees) to text watermark", extra=context)
                    else:
                        # Center position or custom with no rotation
                        can.drawCentredString(watermark_x, watermark_y, watermark_text)
                        logger.debug(f"Drew text watermark at ({watermark_x:.2f}, {watermark_y:.2f}) without rotation", extra=context)
                
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

