"""
Optimized PDF to Word conversion with parallel processing and memory management.
"""

import asyncio
import hashlib
import os
import shutil
import subprocess
import tempfile
import time

import fitz
from django.core.cache import cache
from django.core.files.uploadedfile import UploadedFile
from pdf2docx import Converter
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.api.ocr_utils import extract_text_from_pdf_async
from src.api.pdf_utils import repair_pdf
from src.exceptions import ConversionError, StorageError

logger = get_logger(__name__)


def _get_pdf_hash(pdf_path: str) -> str:
    """Calculate SHA256 hash of PDF file for caching."""
    sha256 = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _normalize_pdf_to_rgb(pdf_path: str, tmp_dir: str, context: dict = None) -> str:
    """
    Re-render PDF pages to RGB-only PDF to avoid PyMuPDF pixmap PNG write errors
    (e.g., CMYK/spot colors).

    Uses caching to avoid re-normalizing the same PDF multiple times.

    Args:
        pdf_path: Input PDF path
        tmp_dir: Directory to place normalized PDF
        context: Logging context (optional)

    Returns:
        Path to normalized RGB PDF
    """
    if context is None:
        context = {}

    start_time = time.time()

    # Check cache first (valid for 1 hour)
    try:
        pdf_hash = _get_pdf_hash(pdf_path)
        cache_key = f"rgb_normalized:{pdf_hash}"
        cached_path = cache.get(cache_key)

        if cached_path and os.path.exists(cached_path):
            elapsed = time.time() - start_time
            logger.info(
                "RGB normalization cache hit",
                extra={
                    **context,
                    "event": "rgb_cache_hit",
                    "elapsed_ms": round(elapsed * 1000, 2),
                },
            )
            return cached_path
    except Exception as e:
        logger.warning(
            f"Cache check failed, proceeding with normalization: {e}",
            extra={**context, "event": "rgb_cache_check_failed"},
        )

    # Cache miss - perform normalization
    rgb_path = os.path.join(tmp_dir, f"rgb_{os.path.basename(pdf_path)}")
    src = None
    out = None
    try:
        src = fitz.open(pdf_path)
        out = fitz.open()

        page_count = src.page_count
        for idx, page in enumerate(src):
            # Use matrix for better quality and performance
            pix = page.get_pixmap(
                alpha=False, colorspace=fitz.csRGB, matrix=fitz.Matrix(1, 1)
            )
            new_page = out.new_page(width=pix.width, height=pix.height)
            rect = fitz.Rect(0, 0, pix.width, pix.height)
            new_page.insert_image(rect, stream=pix.tobytes("png"))

            # Log progress for large PDFs
            if page_count > 10 and (idx + 1) % 10 == 0:
                logger.debug(
                    f"RGB normalization progress: {idx + 1}/{page_count} pages",
                    extra={**context, "event": "rgb_normalization_progress"},
                )

        out.save(rgb_path, garbage=4, deflate=True)

        # Cache the result (1 hour TTL)
        try:
            cache.set(cache_key, rgb_path, 3600)
        except Exception as e:
            logger.warning(
                f"Failed to cache RGB normalized PDF: {e}",
                extra={**context, "event": "rgb_cache_set_failed"},
            )

        elapsed = time.time() - start_time
        logger.info(
            "RGB normalization completed",
            extra={
                **context,
                "event": "rgb_normalization_success",
                "elapsed_ms": round(elapsed * 1000, 2),
                "page_count": page_count,
                "file_size_kb": round(os.path.getsize(rgb_path) / 1024, 2),
            },
        )

        return rgb_path
    finally:
        if out:
            out.close()
        if src:
            src.close()


class OptimizedPDFToWordConverter:
    """
    Optimized PDF to Word converter with parallel processing and memory management.
    """

    def __init__(self):
        self.max_pages_per_batch = 10  # Process pages in batches to control memory
        self.max_text_length = 50000  # Limit OCR text to prevent memory issues
        self.words_per_page = 300  # Words per page for OCR PDF creation

    async def convert_pdf_to_docx_optimized(
        self,
        uploaded_file: UploadedFile,
        suffix: str = "_convertica",
        ocr_enabled: bool = False,
        ocr_language: str = "auto",
        context: dict = None,
        output_path: str = None,
        update_progress: callable = None,
        is_celery_task: bool = False,
    ) -> tuple[str, str]:
        """
        Optimized PDF to DOCX conversion with parallel processing.

        Args:
            uploaded_file: Uploaded PDF file
            suffix: Suffix for output filename
            ocr_enabled: Whether to perform OCR text extraction
            context: Logging context

        Returns:
            Tuple of (input_pdf_path, output_docx_path)
        """
        # Initialize context if not provided
        if context is None or isinstance(context, str):
            context = {}

        # Add Celery task context for logging
        if is_celery_task:
            context["is_celery_task"] = True
            context["conversion_environment"] = "celery_worker"

        if update_progress is None or not callable(update_progress):
            # Create no-op progress callback for batch operations
            def update_progress(*_args, **_kwargs):
                return None

        # Create temporary directory
        tmp_dir = tempfile.mkdtemp(prefix="pdf2docx_opt_")
        context["tmp_dir"] = tmp_dir

        try:
            # Check disk space
            disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=200)
            if not disk_ok:
                raise StorageError(
                    disk_err or "Insufficient disk space", context=context
                )

            # Setup file paths
            safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
            base_name = os.path.splitext(safe_name)[0]
            pdf_path = os.path.join(tmp_dir, safe_name)
            docx_name = f"{base_name}{suffix}.docx"
            docx_path = os.path.join(tmp_dir, docx_name)

            context.update(
                {
                    "pdf_path": pdf_path,
                    "docx_path": docx_path,
                    "ocr_enabled": ocr_enabled,
                    "ocr_language": ocr_language,
                    "conversion_method": "optimized_parallel",
                }
            )

            # Save uploaded file
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)

            # Get page count
            import fitz

            try:
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                doc.close()

                if update_progress:
                    update_progress(40, f"Processing {total_pages} pages...")

            except Exception as e:
                logger.error("Failed to read PDF: %s", e, extra=context)
                raise ConversionError("Failed to read PDF file", context=context) from e

            logger.info(
                "Starting optimized PDF to DOCX conversion - %s",
                "OCR Enhanced" if ocr_enabled else "Standard",
                extra={**context, "event": "conversion_started"},
            )

            # OCR processing if enabled
            ocr_text_content = None
            if ocr_enabled:
                if update_progress:
                    update_progress(50, "Starting OCR processing...")
                ocr_text_content = await self._process_ocr_async(
                    uploaded_file, context, ocr_language
                )

            # Perform optimized conversion
            if update_progress:
                update_progress(70, "Converting to DOCX...")
            await self._perform_conversion_optimized(
                pdf_path, docx_path, ocr_text_content, context
            )

            # Validate output
            if not os.path.exists(docx_path) or os.path.getsize(docx_path) < 1000:
                raise ConversionError(
                    "Output DOCX file is invalid or empty", context=context
                )

            logger.info(
                "PDF to DOCX conversion completed successfully",
                extra={**context, "event": "conversion_success"},
            )

            # Copy to output_path if provided (before cleanup)
            final_docx_path = docx_path
            if output_path:
                shutil.copy2(docx_path, output_path)
                final_docx_path = output_path
                logger.info("Output file copied to: %s", output_path, extra=context)

            return pdf_path, final_docx_path

        finally:
            # Cleanup temporary directory only for Celery tasks
            # For batch processing, the caller (batch view) handles cleanup after ZIP creation
            if is_celery_task and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _process_ocr_async(
        self, uploaded_file: UploadedFile, context: dict, ocr_language: str = "auto"
    ) -> str | None:
        """
        Process OCR with async optimization and memory management.

        Args:
            uploaded_file: Uploaded PDF file
            context: Logging context

        Returns:
            Extracted text or None if OCR failed
        """
        try:
            logger.info(
                "Starting optimized OCR processing",
                extra={**context, "event": "ocr_start"},
            )

            user_language = None
            if ocr_language and ocr_language != "auto":
                user_language = ocr_language
            elif hasattr(uploaded_file, "_request"):
                user_language = getattr(uploaded_file._request, "LANGUAGE_CODE", None)

            # Get confidence threshold from context
            confidence_threshold = context.get("ocr_confidence_threshold", 60)

            # Perform async OCR with memory optimization
            _, extracted_text = await extract_text_from_pdf_async(
                uploaded_file,
                dpi=300,
                user_language=user_language,
                confidence_threshold=confidence_threshold,
            )

            # Limit text length to prevent memory issues
            if len(extracted_text) > self.max_text_length:
                extracted_text = extracted_text[: self.max_text_length] + "..."
                logger.warning(
                    "OCR text truncated to prevent memory issues",
                    extra={**context, "event": "ocr_truncated"},
                )

            context["ocr_extracted_text_length"] = len(extracted_text)
            context["ocr_successful"] = True

            # Force garbage collection
            import gc

            gc.collect()

            logger.info(
                "OCR processing completed successfully",
                extra={**context, "event": "ocr_success"},
            )

            return extracted_text

        except Exception as e:
            logger.warning(
                f"OCR processing failed: {str(e)[:200]}",
                extra={**context, "event": "ocr_failed", "ocr_error": str(e)[:200]},
            )
            context["ocr_successful"] = False
            context["ocr_error"] = str(e)[:200]
            return None

    async def _perform_conversion_optimized(
        self,
        pdf_path: str,
        docx_path: str,
        ocr_text_content: str | None,
        context: dict,
    ):
        """
        Perform optimized PDF to DOCX conversion with memory management.

        Args:
            pdf_path: Path to input PDF
            docx_path: Path to output DOCX
            ocr_text_content: OCR text content if available
            context: Logging context
        """
        pdf_to_convert = pdf_path

        # Create OCR-enhanced PDF if OCR was successful
        if ocr_text_content:
            try:
                pdf_to_convert = await self._create_ocr_pdf_async(
                    ocr_text_content, docx_path, context
                )
            except Exception as e:
                logger.warning(
                    "Failed to create OCR PDF: %s",
                    str(e),
                    extra={**context, "event": "ocr_pdf_failed"},
                )

        # Perform conversion with optimized settings
        await self._convert_with_pdf2docx_async(pdf_to_convert, docx_path, context)

    async def _create_ocr_pdf_async(
        self, ocr_text_content: str, docx_path: str, context: dict
    ) -> str:
        """
        Create OCR-enhanced PDF with extracted text using async processing.

        Args:
            ocr_text_content: Extracted OCR text
            docx_path: Output DOCX path (for temporary directory)
            context: Logging context

        Returns:
            Path to OCR-enhanced PDF
        """
        import fitz

        tmp_dir = tempfile.mkdtemp(prefix="ocr_pdf_")
        ocr_pdf_path = os.path.join(tmp_dir, f"ocr_{os.path.basename(docx_path)}.pdf")

        # Split text into pages and process in batches
        words = ocr_text_content.split()

        # Process pages in batches to control memory
        doc = fitz.open()
        try:
            for i in range(0, len(words), self.words_per_page):
                page_words = words[i : i + self.words_per_page]
                page_text = " ".join(page_words)

                page = doc.new_page(width=595, height=842)  # A4 size
                rect = fitz.Rect(50, 50, 545, 792)  # Margins

                page.insert_textbox(
                    rect, page_text, fontsize=11, fontname="helvetica", align=0
                )

                # Force garbage collection periodically
                if i % (self.words_per_page * 2) == 0:
                    import gc

                    gc.collect()

            # Save OCR PDF with garbage collection
            doc.save(ocr_pdf_path, garbage=4)

            logger.info(
                "Created OCR PDF with extracted text (memory optimized)",
                extra={**context, "event": "ocr_pdf_created"},
            )

        finally:
            doc.close()

        return ocr_pdf_path

    async def _convert_with_pdf2docx_async(
        self, pdf_path: str, docx_path: str, context: dict
    ):
        """
        Convert PDF to DOCX using pdf2docx with optimized settings.

        Falls back to LibreOffice if pdf2docx fails.

        Args:
            pdf_path: Path to input PDF
            docx_path: Path to output DOCX
            context: Logging context
        """

        def _convert(pdf_to_use: str):
            cv = Converter(pdf_to_use)
            try:
                cv.convert(
                    docx_path,
                    start=0,
                    end=None,
                    pages=None,
                    image_dir=None,  # embed images directly
                    multi_processing=False,  # disable multiprocessing for Celery compatibility
                    debug=False,  # disable debug for faster processing
                )
            finally:
                cv.close()

        loop = asyncio.get_event_loop()

        # Timeout for pdf2docx conversion (prevents hanging on complex PDFs)
        PDF2DOCX_TIMEOUT = 180  # 3 minutes max per attempt

        # Try direct conversion first
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, _convert, pdf_path), timeout=PDF2DOCX_TIMEOUT
            )
        except TimeoutError:
            logger.warning(
                f"pdf2docx direct conversion timed out after {PDF2DOCX_TIMEOUT}s",
                extra={**context, "event": "pdf2docx_timeout"},
            )
            # Go straight to LibreOffice fallback on timeout
            success = await loop.run_in_executor(
                None, self._convert_with_libreoffice, pdf_path, docx_path, context
            )
            if success:
                logger.info(
                    "PDF to DOCX conversion completed via LibreOffice (after timeout)",
                    extra={**context, "event": "pdf2docx_complete"},
                )
                return
            raise ConversionError(
                "Conversion timed out and LibreOffice fallback failed",
                context=context,
            )
        except Exception as first_exc:
            msg = str(first_exc).lower()
            if "pixmap must be grayscale or rgb" in msg or "colorspace" in msg:
                logger.warning(
                    "Direct conversion failed due to pixmap colorspace; retrying with RGB-normalized PDF",
                    extra={
                        **context,
                        "event": "retry_with_rgb",
                        "error": str(first_exc)[:200],
                    },
                )
                try:
                    rgb_pdf_path = _normalize_pdf_to_rgb(
                        pdf_path, os.path.dirname(docx_path), context
                    )
                    await asyncio.wait_for(
                        loop.run_in_executor(None, _convert, rgb_pdf_path),
                        timeout=PDF2DOCX_TIMEOUT,
                    )
                    logger.info(
                        "Retry with RGB-normalized PDF succeeded",
                        extra={**context, "event": "retry_with_rgb_success"},
                    )
                    # Clean up the temporary RGB PDF
                    try:
                        os.remove(rgb_pdf_path)
                    except Exception:
                        pass
                    return
                except (TimeoutError, Exception) as rgb_exc:
                    logger.error(
                        "RGB normalization retry failed",
                        extra={
                            **context,
                            "event": "retry_with_rgb_failed",
                            "error": str(rgb_exc)[:200],
                        },
                    )
                    # Fall through to original retry logic

            # If conversion fails, try with repair
            logger.warning(
                "Direct conversion failed, attempting with repair",
                extra={
                    **context,
                    "event": "retry_with_repair",
                    "error": str(first_exc)[:200],
                },
            )

            # Repair to temporary file
            tmp_dir = os.path.dirname(docx_path)
            repaired_pdf_path = os.path.join(
                tmp_dir, f"repaired_{os.path.basename(pdf_path)}"
            )

            try:
                # Use improved repair_pdf with pypdf fallback
                repaired_path = await asyncio.wait_for(
                    loop.run_in_executor(None, repair_pdf, pdf_path, repaired_pdf_path),
                    timeout=60,  # 1 minute max for repair
                )

                # Retry conversion with repaired PDF
                await asyncio.wait_for(
                    loop.run_in_executor(None, _convert, repaired_path),
                    timeout=PDF2DOCX_TIMEOUT,
                )
            except (TimeoutError, Exception) as repair_exc:
                # Last resort: try LibreOffice fallback
                logger.warning(
                    "Repair failed, trying LibreOffice fallback",
                    extra={
                        **context,
                        "event": "trying_libreoffice_fallback",
                        "error": str(repair_exc)[:200],
                    },
                )

                success = await loop.run_in_executor(
                    None, self._convert_with_libreoffice, pdf_path, docx_path, context
                )

                if not success:
                    raise ConversionError(
                        f"All conversion methods failed. Last error: {repair_exc}",
                        context=context,
                    ) from repair_exc

        logger.info(
            "PDF to DOCX conversion completed",
            extra={**context, "event": "pdf2docx_complete"},
        )

    def _convert_with_libreoffice(
        self, pdf_path: str, docx_path: str, context: dict, timeout: int = 120
    ) -> bool:
        """
        Fallback conversion using LibreOffice.

        LibreOffice can handle some PDFs that pdf2docx struggles with,
        especially those with complex colorspaces or corrupted structures.

        Args:
            pdf_path: Path to input PDF
            docx_path: Path to output DOCX
            context: Logging context
            timeout: Timeout in seconds

        Returns:
            True if conversion succeeded, False otherwise
        """
        output_dir = os.path.dirname(docx_path)
        env = os.environ.copy()
        env.update(
            {
                "HOME": output_dir,
                "TMPDIR": output_dir,
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            }
        )

        cmd = [
            "libreoffice",
            "--headless",
            "--nodefault",
            "--nolockcheck",
            "--infilter=writer_pdf_import",
            "--convert-to",
            "docx",
            "--outdir",
            output_dir,
            pdf_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.warning(
                    "LibreOffice PDF->DOCX failed",
                    extra={
                        **context,
                        "event": "libreoffice_fallback_failed",
                        "stderr": result.stderr.decode(errors="replace")[:200],
                    },
                )
                return False

            # LibreOffice creates file with original name, find and rename it
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            created_docx = os.path.join(output_dir, f"{base_name}.docx")

            if os.path.exists(created_docx):
                if created_docx != docx_path:
                    shutil.move(created_docx, docx_path)
                logger.info(
                    "LibreOffice fallback succeeded",
                    extra={**context, "event": "libreoffice_fallback_success"},
                )
                return True

            # Search for any created docx
            for f in os.listdir(output_dir):
                if f.endswith(".docx") and f != os.path.basename(docx_path):
                    shutil.move(os.path.join(output_dir, f), docx_path)
                    return True

            return False

        except subprocess.TimeoutExpired:
            logger.warning(
                f"LibreOffice fallback timed out after {timeout}s",
                extra={**context, "event": "libreoffice_fallback_timeout"},
            )
            return False
        except FileNotFoundError:
            logger.warning(
                "LibreOffice not installed, fallback unavailable",
                extra={**context, "event": "libreoffice_not_found"},
            )
            return False
        except Exception as e:
            logger.warning(
                f"LibreOffice fallback error: {e}",
                extra={**context, "event": "libreoffice_fallback_error"},
            )
            return False


async def convert_pdf_to_docx_optimized(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
    ocr_enabled: bool = False,
    ocr_language: str = "auto",
    context: dict = None,
    output_path: str = None,
    update_progress: callable = None,
    is_celery_task: bool = False,
) -> tuple[str, str]:
    """
    Optimized PDF to DOCX conversion with parallel processing.

    Args:
        uploaded_file: Uploaded PDF file
        suffix: Suffix for output filename
        ocr_enabled: Whether to perform OCR text extraction
        context: Logging context
        output_path: Path to save the output file (optional)
        update_progress: Progress update callback function (optional)

    Returns:
        Tuple of (input_pdf_path, output_docx_path)
    """
    converter = OptimizedPDFToWordConverter()
    return await converter.convert_pdf_to_docx_optimized(
        uploaded_file=uploaded_file,
        suffix=suffix,
        ocr_enabled=ocr_enabled,
        ocr_language=ocr_language,
        context=context,
        output_path=output_path,
        update_progress=update_progress,
        is_celery_task=is_celery_task,
    )
