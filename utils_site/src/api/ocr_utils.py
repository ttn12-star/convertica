"""
OCR utilities for premium users only.
Provides text extraction from PDFs using Tesseract OCR.
Supports all site languages: ar, en, es, hi, id, pl, ru
"""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import pytesseract
from django.core.files.uploadedfile import UploadedFile
from pdf2image import convert_from_path

from utils_site.src.exceptions import ConversionError, StorageError

from .file_validation import check_disk_space, sanitize_filename
from .logging_utils import get_logger

logger = get_logger(__name__)

# Thread pool for async OCR processing
OCR_THREAD_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")

# Mapping of site languages to Tesseract language codes
SITE_LANGUAGES = {
    "ar": "ara",  # Arabic
    "zh-cn": "chi_sim",  # Chinese (Simplified)
    "zh-tw": "chi_tra",  # Chinese (Traditional)
    "de": "deu",  # German
    "en": "eng",  # English
    "es": "spa",  # Spanish
    "fr": "fra",  # French
    "hi": "hin",  # Hindi
    "id": "ind",  # Indonesian
    "it": "ita",  # Italian
    "ja": "jpn",  # Japanese
    "ko": "kor",  # Korean
    "pl": "pol",  # Polish
    "pt": "por",  # Portuguese
    "ru": "rus",  # Russian
    "tr": "tur",  # Turkish
    "uk": "ukr",  # Ukrainian
}

# Default language if user language not supported
DEFAULT_OCR_LANG = "eng"


def get_ocr_language_code(user_language: str = None) -> str:
    """
    Convert site language code to Tesseract language code.

    Args:
        user_language: User's preferred language (e.g., 'en', 'ru')

    Returns:
        Tesseract language code for OCR
    """
    if not user_language:
        return DEFAULT_OCR_LANG

    # Normalize language code
    user_language = user_language.lower().strip()

    # Map to Tesseract code
    tesseract_lang = SITE_LANGUAGES.get(user_language, DEFAULT_OCR_LANG)

    logger.debug(
        f"Language mapping: {user_language} -> {tesseract_lang}",
        extra={
            "event": "ocr_language_mapping",
            "user_lang": user_language,
            "tesseract_lang": tesseract_lang,
        },
    )

    return tesseract_lang


async def extract_text_from_pdf_async(
    uploaded_file: UploadedFile,
    dpi: int = 150,  # Optimized for 4GB servers
    user_language: str = None,
) -> tuple[str, str]:
    """
    Async version of extract_text_from_pdf for better performance.

    Uses ThreadPoolExecutor to run OCR in background threads.
    Supports all site languages automatically.
    """
    loop = asyncio.get_event_loop()

    # Run OCR in thread pool to avoid blocking
    return await loop.run_in_executor(
        OCR_THREAD_POOL, extract_text_from_pdf, uploaded_file, dpi, user_language
    )


def extract_text_from_pdf(
    uploaded_file: UploadedFile, dpi: int = 300, user_language: str = None
) -> tuple[str, str]:
    """
    Extract text from PDF using OCR for premium users only.

    Args:
        uploaded_file: Uploaded PDF file
        dpi: DPI for image processing (default 300)
        user_language: User's preferred language (e.g., 'en', 'ru')

    Returns:
        Tuple[str, str]: (pdf_path, text_content)

    Raises:
        ConversionError: If OCR processing fails
        StorageError: If disk space insufficient
    """
    # Get OCR language code from user language
    ocr_lang = get_ocr_language_code(user_language)

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "extract_text_from_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
        "dpi": dpi,
        "user_language": user_language,
        "ocr_lang": ocr_lang,
    }

    tmp_dir = tempfile.mkdtemp(prefix="ocr_")
    context["tmp_dir"] = tmp_dir

    try:
        # Check disk space
        disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=500)
        if not disk_ok:
            raise StorageError(
                disk_err or "Insufficient disk space for OCR", context=context
            )

        # Save PDF temporarily
        pdf_path = os.path.join(tmp_dir, safe_name)
        context["pdf_path"] = pdf_path

        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)
        except OSError as e:
            raise StorageError(
                f"Failed to write uploaded file: {e}", context=context
            ) from e

        # Convert PDF to images for OCR
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            context["total_pages"] = len(images)
        except Exception as e:
            raise ConversionError(
                f"Failed to convert PDF to images: {e}", context=context
            ) from e

        # Extract text from each page
        extracted_texts = []
        for i, image in enumerate(images):
            try:
                text = pytesseract.image_to_string(image, lang=ocr_lang)
                extracted_texts.append(text)
                context[f"page_{i}_text_length"] = len(text)
            except Exception as e:
                logger.warning(
                    f"OCR failed for page {i+1}",
                    extra={**context, "page": i + 1, "error": str(e)[:200]},
                )
                extracted_texts.append("")  # Add empty text for failed page

        # Combine all text
        full_text = "\n\n".join(extracted_texts)
        context["total_text_length"] = len(full_text)

        logger.info(
            "OCR extraction completed", extra={**context, "event": "ocr_success"}
        )

        return pdf_path, full_text

    except (StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during OCR extraction",
            extra={**context, "event": "ocr_unexpected_error"},
        )
        raise ConversionError(
            f"Unexpected error during OCR: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e


def create_searchable_pdf(
    uploaded_file: UploadedFile, output_text: str, suffix: str = "_ocr"
) -> str:
    """
    Create a searchable PDF by overlaying OCR text on original PDF.
    For premium users only.

    Args:
        uploaded_file: Original PDF file
        output_text: Extracted OCR text
        suffix: Suffix for output filename

    Returns:
        str: Path to searchable PDF

    Raises:
        ConversionError: If PDF creation fails
    """
    import fitz  # PyMuPDF

    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    base_name = os.path.splitext(safe_name)[0]
    context = {
        "function": "create_searchable_pdf",
        "input_filename": safe_name,
        "output_text_length": len(output_text),
    }

    tmp_dir = tempfile.mkdtemp(prefix="searchable_pdf_")
    context["tmp_dir"] = tmp_dir

    try:
        # Save original PDF
        pdf_path = os.path.join(tmp_dir, safe_name)
        with open(pdf_path, "wb") as f:
            for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                f.write(chunk)

        # Create searchable PDF
        output_name = f"{base_name}{suffix}.pdf"
        output_path = os.path.join(tmp_dir, output_name)
        context.update({"pdf_path": pdf_path, "output_path": output_path})

        try:
            doc = fitz.open(pdf_path)

            # Simple text overlay - in production, this would need more sophisticated
            # positioning to match the original layout
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Insert invisible text layer for searchability
                # This is a simplified approach - real implementation would need
                # proper text positioning from OCR coordinates
                rect = fitz.Rect(50, 50, 500, 800)  # Default page area
                page.insert_text(
                    rect.point_tl, output_text[:1000], fontsize=0
                )  # Invisible text

            doc.save(output_path)
            doc.close()

        except Exception as e:
            raise ConversionError(
                f"Failed to create searchable PDF: {e}", context=context
            ) from e

        logger.info(
            "Searchable PDF created successfully",
            extra={**context, "event": "searchable_pdf_success"},
        )

        return output_path

    except ConversionError:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error creating searchable PDF",
            extra={**context, "event": "searchable_pdf_unexpected_error"},
        )
        raise ConversionError(
            f"Unexpected error creating searchable PDF: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e


def is_premium_user(user) -> bool:
    """
    Check if user has premium subscription.

    Args:
        user: Django user object

    Returns:
        bool: True if user is premium
    """
    if not user.is_authenticated:
        return False

    # Check if user has active premium subscription
    if hasattr(user, "is_premium") and user.is_premium:
        # Additional check for active subscription
        if hasattr(user, "is_subscription_active"):
            return user.is_subscription_active()
        return True

    return False
