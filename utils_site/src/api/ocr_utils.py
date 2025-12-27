"""
OCR utilities for premium users only.
Provides advanced text extraction from PDFs using Tesseract OCR.

Features:
- Adaptive image preprocessing (deskew, contrast enhancement, binarization)
- Multi-language support (17 languages) with auto-detection
- Confidence-based filtering to remove low-quality OCR results
- Optimized Tesseract configuration (LSTM engine, PSM 6)
- DPI 300 for high-quality text recognition
- Async processing with ThreadPoolExecutor

Supported languages: ar, zh-cn, zh-tw, de, en, es, fr, hi, id, it, ja, ko, pl, pt, ru, tr, uk
"""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytesseract
from django.core.files.uploadedfile import UploadedFile
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
from scipy import ndimage
from src.exceptions import ConversionError, StorageError

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

    Supports auto-detection by combining multiple languages when user_language
    is None or 'auto'. This allows Tesseract to automatically detect the best
    language for each text region.

    Args:
        user_language: User's preferred language (e.g., 'en', 'ru', 'auto')

    Returns:
        Tesseract language code for OCR (single or combined)
    """
    # Auto-detection: use most common languages combined
    # Tesseract will automatically pick the best match
    if not user_language or user_language.lower().strip() == "auto":
        # Combine top languages: English, Russian, German, French, Spanish, Chinese
        auto_langs = "eng+rus+deu+fra+spa+chi_sim"
        logger.debug(
            f"Auto-detection enabled, using combined languages: {auto_langs}",
            extra={
                "event": "ocr_language_auto",
                "combined_langs": auto_langs,
            },
        )
        return auto_langs

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


def calculate_image_contrast(image: Image.Image) -> float:
    """
    Calculate image contrast using standard deviation of pixel values.

    Args:
        image: PIL Image in grayscale

    Returns:
        Contrast value (0-100+)
    """
    img_array = np.array(image)
    return float(np.std(img_array))


def detect_skew_angle(image: Image.Image) -> float:
    """
    Detect skew angle of text in image using projection profile method.

    Args:
        image: PIL Image in grayscale

    Returns:
        Skew angle in degrees (-45 to 45)
    """
    try:
        # Convert to numpy array
        img_array = np.array(image)

        # Binarize image for edge detection
        threshold = np.mean(img_array)
        binary = img_array < threshold

        # Calculate projection profiles at different angles
        angles = np.arange(-5, 6, 0.5)  # Check -5 to +5 degrees
        scores = []

        for angle in angles:
            rotated = ndimage.rotate(binary, angle, reshape=False, order=0)
            # Sum along vertical axis (projection profile)
            projection = np.sum(rotated, axis=1)
            # Score is variance of projection (higher = more aligned)
            scores.append(np.var(projection))

        # Find angle with maximum variance (best alignment)
        best_angle = angles[np.argmax(scores)]

        # Only return angle if significant (> 0.5 degrees)
        if abs(best_angle) > 0.5:
            return float(best_angle)
        return 0.0

    except Exception as e:
        logger.warning(
            f"Skew detection failed: {e}", extra={"event": "skew_detection_failed"}
        )
        return 0.0


def preprocess_image_for_ocr(image: Image.Image, adaptive: bool = True) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy with adaptive parameters.

    Applies:
    - Grayscale conversion
    - Deskew (rotation correction)
    - Adaptive contrast enhancement
    - Sharpening
    - Adaptive binarization
    - Noise removal

    Args:
        image: PIL Image object
        adaptive: Use adaptive preprocessing based on image quality

    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    if image.mode != "L":
        image = image.convert("L")

    # Deskew: correct rotation for better OCR
    if adaptive:
        skew_angle = detect_skew_angle(image)
        if abs(skew_angle) > 0.5:
            image = image.rotate(skew_angle, expand=True, fillcolor=255)
            logger.debug(
                f"Deskewed image by {skew_angle:.2f} degrees",
                extra={"event": "image_deskewed", "angle": skew_angle},
            )

    # Adaptive contrast enhancement based on image quality
    if adaptive:
        contrast = calculate_image_contrast(image)
        # Low contrast images need more enhancement
        if contrast < 30:
            enhance_factor = 2.5  # Very low contrast
        elif contrast < 50:
            enhance_factor = 2.0  # Low contrast
        elif contrast < 70:
            enhance_factor = 1.5  # Medium contrast
        else:
            enhance_factor = 1.2  # Good contrast

        logger.debug(
            f"Image contrast: {contrast:.1f}, enhancement: {enhance_factor}x",
            extra={
                "event": "adaptive_contrast",
                "contrast": contrast,
                "factor": enhance_factor,
            },
        )
    else:
        enhance_factor = 1.5

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(enhance_factor)

    # Apply sharpening
    image = image.filter(ImageFilter.SHARPEN)

    # Adaptive binarization using Otsu's method approximation
    if adaptive:
        img_array = np.array(image)
        # Calculate optimal threshold (Otsu's method approximation)
        hist, bins = np.histogram(img_array.ravel(), bins=256, range=(0, 256))
        # Weighted average for threshold
        total = img_array.size
        sum_total = np.sum(np.arange(256) * hist)
        sum_background = 0
        weight_background = 0
        max_variance = 0
        threshold = 128

        for i in range(256):
            weight_background += hist[i]
            if weight_background == 0:
                continue
            weight_foreground = total - weight_background
            if weight_foreground == 0:
                break

            sum_background += i * hist[i]
            mean_background = sum_background / weight_background
            mean_foreground = (sum_total - sum_background) / weight_foreground

            variance = (
                weight_background
                * weight_foreground
                * (mean_background - mean_foreground) ** 2
            )
            if variance > max_variance:
                max_variance = variance
                threshold = i

        logger.debug(
            f"Adaptive threshold: {threshold}",
            extra={"event": "adaptive_threshold", "threshold": threshold},
        )
    else:
        threshold = 128

    # Apply binarization
    image = image.point(lambda p: 255 if p > threshold else 0)

    # Remove noise with median filter
    image = image.filter(ImageFilter.MedianFilter(size=3))

    return image


async def extract_text_from_pdf_async(
    uploaded_file: UploadedFile,
    dpi: int = 300,  # Tesseract recommends 300-400 DPI for optimal OCR quality
    user_language: str = None,
    confidence_threshold: int = 60,
) -> tuple[str, str]:
    """
    Async version of extract_text_from_pdf for better performance.

    Uses ThreadPoolExecutor to run OCR in background threads.
    Supports all site languages automatically with adaptive preprocessing.

    Args:
        uploaded_file: Uploaded PDF file
        dpi: DPI for image processing (default 300)
        user_language: User's preferred language or 'auto' for auto-detection
        confidence_threshold: Minimum confidence for OCR words (0-100, default 60)

    Returns:
        Tuple[str, str]: (pdf_path, extracted_text)
    """
    loop = asyncio.get_event_loop()

    # Run OCR in thread pool to avoid blocking
    return await loop.run_in_executor(
        OCR_THREAD_POOL,
        extract_text_from_pdf,
        uploaded_file,
        dpi,
        user_language,
        confidence_threshold,
    )


def extract_text_from_pdf(
    uploaded_file: UploadedFile,
    dpi: int = 300,
    user_language: str = None,
    confidence_threshold: int = 60,
) -> tuple[str, str]:
    """
    Extract text from PDF using OCR for premium users only.

    Features:
    - Adaptive preprocessing (deskew, contrast, binarization)
    - Multi-language auto-detection
    - Confidence-based filtering
    - Optimized Tesseract config

    Args:
        uploaded_file: Uploaded PDF file
        dpi: DPI for image processing (default 300, recommended 300-400)
        user_language: User's preferred language or 'auto' for auto-detection
        confidence_threshold: Minimum confidence for words (0-100, default 60)

    Returns:
        Tuple[str, str]: (pdf_path, extracted_text)

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

        # Extract text from each page with preprocessing and confidence filtering
        extracted_texts = []
        # Tesseract config: PSM 6 = uniform block of text, OEM 1 = LSTM engine only
        tesseract_config = r"--oem 1 --psm 6"
        # Use provided confidence_threshold parameter

        for i, image in enumerate(images):
            try:
                # Preprocess image for better OCR quality
                processed_image = preprocess_image_for_ocr(image)

                # Extract text with confidence data
                ocr_data = pytesseract.image_to_data(
                    processed_image,
                    lang=ocr_lang,
                    config=tesseract_config,
                    output_type=pytesseract.Output.DICT,
                )

                # Filter by confidence and reconstruct text
                filtered_words = []
                low_confidence_count = 0
                total_words = 0

                for j, word in enumerate(ocr_data["text"]):
                    if word.strip():  # Non-empty word
                        total_words += 1
                        conf = (
                            int(ocr_data["conf"][j])
                            if ocr_data["conf"][j] != "-1"
                            else 0
                        )

                        if conf >= confidence_threshold:
                            filtered_words.append(word)
                        else:
                            low_confidence_count += 1

                # Join words with spaces, preserving line breaks
                text = " ".join(filtered_words)

                # Log confidence statistics
                if total_words > 0:
                    filtered_percentage = (low_confidence_count / total_words) * 100
                    logger.debug(
                        f"Page {i+1}: filtered {low_confidence_count}/{total_words} words ({filtered_percentage:.1f}%)",
                        extra={
                            "event": "ocr_confidence_filter",
                            "page": i + 1,
                            "total_words": total_words,
                            "filtered_words": low_confidence_count,
                            "threshold": confidence_threshold,
                        },
                    )

                extracted_texts.append(text)
                context[f"page_{i}_text_length"] = len(text)
                context[f"page_{i}_filtered_words"] = low_confidence_count
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
