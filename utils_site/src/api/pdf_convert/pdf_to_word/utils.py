# services/convert.py
import os
import shutil
import tempfile

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from pdf2docx import Converter

from ....exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)
from ...file_validation import check_disk_space, sanitize_filename, validate_output_file
from ...logging_utils import get_logger
from ...optimization_manager import optimization_manager
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


async def convert_pdf_to_docx(
    uploaded_file: UploadedFile, suffix: str = "_convertica", ocr_enabled: bool = False
) -> tuple[str, str]:
    """
    Convert PDF to DOCX using adaptive optimization.

    Args:
        uploaded_file: Uploaded PDF file
        suffix: Suffix for output filename
        ocr_enabled: Whether to use OCR processing
    """
    return await optimization_manager.convert_pdf_to_docx(
        uploaded_file, suffix=suffix, ocr_enabled=ocr_enabled
    )


async def _convert_pdf_to_docx_sequential(
    uploaded_file: UploadedFile,
    suffix: str,
    ocr_enabled: bool,
    context: dict,
    ocr_language: str = "auto",
) -> tuple[str, str]:
    """
    Original sequential PDF to DOCX conversion (fallback).
    """
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    base_name = os.path.splitext(safe_name)[0]

    tmp_dir = tempfile.mkdtemp(prefix="pdf2docx_")
    context["tmp_dir"] = tmp_dir

    try:
        # Check disk space
        disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=200)
        if not disk_ok:
            raise StorageError(disk_err or "Insufficient disk space", context=context)

        # File paths
        pdf_path = os.path.join(tmp_dir, safe_name)
        docx_name = f"{base_name}{suffix}.docx"
        docx_path = os.path.join(tmp_dir, docx_name)
        context.update({"pdf_path": pdf_path, "docx_path": docx_path})

        # Write uploaded file in large chunks
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)
        except OSError as e:
            raise StorageError(f"Failed to write uploaded file: {e}", context=context)

        # Log conversion type
        logger.info(
            f"Starting PDF to DOCX conversion - {'OCR Enhanced' if ocr_enabled else 'Standard'}",
            extra={
                **context,
                "event": "conversion_started",
                "ocr_enabled": ocr_enabled,
                "conversion_type": "ocr_enhanced" if ocr_enabled else "standard",
            },
        )

        # Quick page count check and text detection
        import fitz  # PyMuPDF

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # Check if PDF already has extractable text
            has_text = False
            text_sample = ""
            for page_num in range(min(3, total_pages)):  # Check first 3 pages
                page = doc[page_num]
                page_text = page.get_text().strip()
                if len(page_text) > 50:  # If page has meaningful text
                    has_text = True
                    text_sample = page_text[:200]
                    break

            doc.close()

            logger.info(
                f"PDF analysis: {total_pages} pages, {'text-based' if has_text else 'image-based/scanned'}",
                extra={
                    **context,
                    "total_pages": total_pages,
                    "has_extractable_text": has_text,
                    "text_sample_length": len(text_sample),
                },
            )
        except Exception as e:
            raise InvalidPDFError(f"Failed to read PDF: {e}", context=context) from e

        # OCR processing - only for scanned/image-based PDFs
        ocr_text_content = None
        should_use_ocr = ocr_enabled and not has_text

        if ocr_enabled and has_text:
            logger.info(
                "OCR skipped: PDF already contains extractable text. Using standard conversion for better quality.",
                extra={
                    **context,
                    "event": "ocr_skipped",
                    "reason": "text_already_present",
                },
            )

        if should_use_ocr:
            try:
                logger.info(
                    "Starting OCR processing (user requested)",
                    extra={**context, "event": "ocr_start"},
                )

                # Try async OCR first, fallback to sync if needed
                try:
                    import asyncio

                    from src.api.ocr_utils import extract_text_from_pdf_async

                    # Use OCR language from parameter, fallback to request language
                    user_language = ocr_language if ocr_language != "auto" else None
                    if user_language is None and hasattr(uploaded_file, "_request"):
                        user_language = getattr(
                            uploaded_file._request, "LANGUAGE_CODE", None
                        )

                    # Get confidence threshold from context
                    confidence_threshold = context.get("ocr_confidence_threshold", 60)

                    # Run async OCR in event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        _, extracted_text = loop.run_until_complete(
                            extract_text_from_pdf_async(
                                uploaded_file,
                                dpi=300,
                                user_language=user_language,
                                confidence_threshold=confidence_threshold,
                            )
                        )
                    finally:
                        loop.close()

                except (ImportError, RuntimeError):
                    # Fallback to sync OCR
                    from src.api.ocr_utils import extract_text_from_pdf

                    # Use OCR language from parameter, fallback to request language
                    user_language = ocr_language if ocr_language != "auto" else None
                    if user_language is None and hasattr(uploaded_file, "_request"):
                        user_language = getattr(
                            uploaded_file._request, "LANGUAGE_CODE", None
                        )

                    # Get confidence threshold from context
                    confidence_threshold = context.get("ocr_confidence_threshold", 60)

                    _, extracted_text = extract_text_from_pdf(
                        uploaded_file,
                        dpi=300,
                        user_language=user_language,
                        confidence_threshold=confidence_threshold,
                    )

                # Limit text length to prevent memory issues
                if len(extracted_text) > 50000:  # Limit to ~50K characters
                    extracted_text = extracted_text[:50000] + "..."
                    logger.warning(
                        "OCR text truncated to prevent memory issues",
                        extra={**context, "event": "ocr_truncated"},
                    )

                ocr_text_content = extracted_text
                context["ocr_extracted_text_length"] = len(extracted_text)
                context["ocr_successful"] = True

                # Force garbage collection to free memory
                import gc

                gc.collect()

                logger.info(
                    "OCR processing completed successfully",
                    extra={**context, "event": "ocr_success"},
                )
            except (ConversionError, StorageError, OSError) as ocr_exc:
                logger.warning(
                    "OCR processing failed, continuing with standard conversion: %s",
                    str(ocr_exc)[:200],
                    extra={
                        **context,
                        "event": "ocr_failed",
                        "ocr_error": str(ocr_exc)[:200],
                    },
                )
                context["ocr_successful"] = False
                context["ocr_error"] = str(ocr_exc)[:200]

        context.update(
            {
                "total_pages": total_pages,
                "ocr_requested": ocr_enabled,
                "ocr_actually_used": should_use_ocr,
                "pdf_has_text": has_text,
            }
        )

        # Optimized conversion function
        def perform_conversion(input_pdf, output_docx):
            # If OCR was successful, create enhanced PDF with text layer
            pdf_to_convert = input_pdf
            if ocr_text_content and ocr_enabled:
                try:
                    # Create simple text PDF with OCR content - memory optimized
                    import fitz  # PyMuPDF

                    tmp_dir = tempfile.mkdtemp(prefix="ocr_pdf_")
                    ocr_pdf_path = os.path.join(
                        tmp_dir, f"ocr_{os.path.basename(output_docx)}.pdf"
                    )

                    # Create new PDF with OCR text
                    doc = fitz.open()

                    # Split text into pages (reduced from 500 to 300 words per page)
                    words = ocr_text_content.split()
                    words_per_page = 300  # Reduced for memory optimization

                    for i in range(0, len(words), words_per_page):
                        page_words = words[i : i + words_per_page]
                        page_text = " ".join(page_words)

                        # Create page with text
                        page = doc.new_page(width=595, height=842)  # A4 size
                        rect = fitz.Rect(50, 50, 545, 792)  # Margins

                        # Insert text
                        page.insert_textbox(
                            rect, page_text, fontsize=11, fontname="helvetica", align=0
                        )

                        # Force garbage collection after each page
                        if i % (words_per_page * 2) == 0:
                            import gc

                            gc.collect()

                    # Save OCR PDF
                    doc.save(ocr_pdf_path, garbage=4)  # Enable garbage collection
                    doc.close()

                    # Force cleanup
                    import gc

                    gc.collect()

                    pdf_to_convert = ocr_pdf_path
                    logger.info(
                        "Created OCR PDF with extracted text (memory optimized)",
                        extra={**context, "event": "ocr_pdf_created"},
                    )

                except (ConversionError, StorageError, OSError) as e:
                    logger.warning(
                        "Failed to create OCR PDF, using original: %s",
                        str(e),
                        extra={**context, "event": "ocr_pdf_failed"},
                    )

            cv = Converter(pdf_to_convert)
            try:
                # Optimized settings for faster conversion
                cv.convert(
                    output_docx,
                    start=0,
                    end=None,
                    pages=None,
                    image_dir=None,  # embed images directly
                    multi_processing=False,  # disable multiprocessing to avoid Celery conflicts
                    debug=False,  # disable debug for faster processing
                )
            finally:
                cv.close()

        # Perform conversion, retry with repair only if needed
        conversion_pdf_path = pdf_path
        repair_attempted = False
        ocr_fallback_used = False

        try:
            perform_conversion(conversion_pdf_path, docx_path)
        except Exception as first_exc:
            repair_attempted = True
            logger.warning(
                "Direct conversion failed, attempting with repair",
                extra={
                    **context,
                    "event": "retry_with_repair",
                    "error": str(first_exc)[:200],
                },
            )
            try:
                repaired_pdf_path = os.path.join(tmp_dir, f"repaired_{safe_name}")
                conversion_pdf_path = repair_pdf(pdf_path, repaired_pdf_path)
                perform_conversion(conversion_pdf_path, docx_path)
            except Exception as second_exc:
                # If repair also fails, try OCR-based conversion as last resort
                logger.warning(
                    "Repair failed, attempting OCR-based conversion as fallback",
                    extra={
                        **context,
                        "event": "ocr_fallback",
                        "error": str(second_exc)[:200],
                    },
                )
                ocr_fallback_used = True
                # Force OCR conversion for severely corrupted PDFs
                from ...ocr_utils import convert_pdf_to_images_and_ocr

                try:
                    # Convert PDF to images and OCR back to text
                    ocr_text = convert_pdf_to_images_and_ocr(pdf_path)

                    # Create DOCX from OCR text
                    from docx import Document

                    doc = Document()
                    doc.add_paragraph(ocr_text)
                    doc.save(docx_path)

                    logger.info(
                        "OCR fallback successful for corrupted PDF",
                        extra={**context, "event": "ocr_fallback_success"},
                    )
                except Exception as ocr_exc:
                    logger.error(
                        "All conversion methods failed",
                        extra={
                            **context,
                            "event": "all_methods_failed",
                            "ocr_error": str(ocr_exc)[:200],
                        },
                    )
                    raise ConversionError(
                        f"PDF is too corrupted to convert. Tried: standard conversion, repair, and OCR. Last error: {ocr_exc}",
                        context=context,
                    )

        # Validate output DOCX
        valid, val_err = validate_output_file(docx_path, min_size=1000, context=context)
        if not valid:
            raise ConversionError(val_err or "Output file invalid", context=context)

        logger.info(
            "PDF to DOCX conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "repair_attempted": repair_attempted,
                "ocr_fallback_used": ocr_fallback_used,
                "output_size_bytes": os.path.getsize(docx_path),
                "ocr_enabled": ocr_enabled,
                "conversion_type": (
                    "ocr_fallback"
                    if ocr_fallback_used
                    else ("ocr_enhanced" if ocr_enabled else "standard")
                ),
            },
        )

        return pdf_path, docx_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error in PDF to DOCX conversion",
            extra={**context, "event": "unexpected_error", "error": str(e)},
        )
        raise ConversionError(f"Unexpected error: {e}", context=context)

    finally:
        # Cleanup temporary directory
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
