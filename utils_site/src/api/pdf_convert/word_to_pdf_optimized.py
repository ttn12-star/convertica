"""
Optimized Word to PDF conversion with parallel processing and memory management.
"""

import asyncio
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.api.parallel_processing import get_optimal_batch_size
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)

# Magic numbers for DOCX/DOC validation
DOCX_MAGIC = b"PK\x03\x04"
DOC_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class OptimizedWordToPDFConverter:
    """
    Optimized Word to PDF converter with parallel processing and memory management.
    """

    def __init__(self):
        self.chunk_size = 512 * 1024  # 512 KB chunks for file writing
        self.timeout_seconds = 180  # 3 minutes timeout for LibreOffice
        self.max_retries = 2  # Maximum retry attempts

    async def convert_word_to_pdf_optimized(
        self,
        uploaded_file: UploadedFile,
        suffix: str = "_convertica",
        context: dict = None,
        is_celery_task: bool = False,
    ) -> tuple[str, str]:
        """
        Optimized Word to PDF conversion with parallel processing.

        Args:
            uploaded_file: Uploaded Word file
            suffix: Suffix for output filename
            context: Logging context

        Returns:
            Tuple of (input_docx_path, output_pdf_path)
        """
        if context is None:
            context = {}

        # Add Celery task context for logging
        if is_celery_task:
            context["is_celery_task"] = True
            context["conversion_environment"] = "celery_worker"

        # Create temporary directory
        tmp_dir = tempfile.mkdtemp(prefix="doc2pdf_opt_")
        context["tmp_dir"] = tmp_dir

        try:
            # Check disk space
            disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=200)
            if not disk_ok:
                raise StorageError(
                    disk_err or "Insufficient disk space", context=context
                )

            # Setup file paths
            original_filename = uploaded_file.name if uploaded_file.name else "unknown"
            safe_name = sanitize_filename(
                get_valid_filename(os.path.basename(original_filename))
            )

            # Ensure proper extension
            if not safe_name.lower().endswith((".doc", ".docx")):
                original_ext = os.path.splitext(original_filename)[1].lower()
                if original_ext in (".doc", ".docx"):
                    safe_name = os.path.splitext(safe_name)[0] + original_ext

            docx_path = os.path.join(tmp_dir, safe_name)
            base_name, _ = os.path.splitext(safe_name)
            pdf_name = f"{base_name}{suffix}.pdf"
            pdf_path = os.path.join(tmp_dir, pdf_name)

            context.update(
                {
                    "docx_path": docx_path,
                    "pdf_path": pdf_path,
                    "input_filename": safe_name,
                    "original_filename": original_filename,
                    "input_size": uploaded_file.size,
                    "conversion_method": "optimized_parallel",
                }
            )

            # Validate magic number before writing
            await self._validate_magic_number_async(uploaded_file, context)

            # Save uploaded file
            await self._save_uploaded_file_async(uploaded_file, docx_path, context)

            # Validate Word file (temporarily disabled for testing)
            # await self._validate_word_file_async(docx_path, context)

            # Perform optimized LibreOffice conversion
            await self._convert_with_libreoffice_async(docx_path, pdf_path, context)

            # Validate output - check for both suffixed and original filename
            expected_pdf_path = pdf_path
            original_pdf_path = os.path.join(tmp_dir, f"{base_name}.pdf")

            if os.path.exists(expected_pdf_path):
                pdf_path = expected_pdf_path
            elif os.path.exists(original_pdf_path):
                pdf_path = original_pdf_path
                # Update context with actual path
                context["actual_pdf_path"] = original_pdf_path
                logger.info(
                    f"Using original PDF path: {original_pdf_path}", extra=context
                )
            else:
                raise ConversionError(
                    "Output PDF file was not created", context=context
                )

            # Log file size for debugging
            file_size = os.path.getsize(pdf_path)
            logger.info(f"PDF file created with size: {file_size} bytes", extra=context)

            if file_size == 0:
                raise ConversionError("Output PDF file is empty", context=context)

            logger.info(
                "Word to PDF conversion completed successfully",
                extra={**context, "event": "conversion_success"},
            )

            return docx_path, pdf_path

        finally:
            # Cleanup temporary directory (skip for Celery tasks - they handle cleanup)
            if not is_celery_task and os.path.exists(tmp_dir):
                import shutil

                shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _validate_magic_number_async(
        self, uploaded_file: UploadedFile, context: dict
    ):
        """Validate Word file magic number asynchronously."""

        def _validate():
            try:
                header = uploaded_file.read(16)
                uploaded_file.seek(0)
                if not (header.startswith(DOCX_MAGIC) or header.startswith(DOC_MAGIC)):
                    raise InvalidPDFError(
                        "File does not appear to be a valid Word document"
                    )
            except Exception as e:
                raise InvalidPDFError(f"Failed to validate Word file: {e}") from e

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _validate)

        logger.debug(
            "Magic number validation passed",
            extra={**context, "event": "magic_number_valid"},
        )

    async def _save_uploaded_file_async(
        self, uploaded_file: UploadedFile, docx_path: str, context: dict
    ):
        """Save uploaded file asynchronously with controlled chunks."""

        def _save():
            try:
                with open(docx_path, "wb") as f:
                    for chunk in uploaded_file.chunks(chunk_size=self.chunk_size):
                        f.write(chunk)
            except OSError as err:
                raise StorageError(
                    f"Failed to write Word file to temp: {err}",
                    context={**context, "error_type": type(err).__name__},
                ) from err

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)

        logger.debug(
            "Word file written successfully",
            extra={**context, "event": "file_write_success"},
        )

    async def _validate_word_file_async(self, docx_path: str, context: dict):
        """Validate Word file asynchronously."""

        def _validate():
            from src.api.file_validation import validate_word_file

            is_valid, validation_error = validate_word_file(docx_path, context)
            if not is_valid:
                raise InvalidPDFError(
                    validation_error or "Invalid Word file structure", context=context
                )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _validate)

        logger.debug(
            "Word file validation passed",
            extra={**context, "event": "file_validation_success"},
        )

    async def _convert_with_libreoffice_async(
        self, docx_path: str, pdf_path: str, context: dict
    ):
        """
        Perform LibreOffice conversion with optimization and retry logic.

        Args:
            docx_path: Path to input Word document
            pdf_path: Path to output PDF
            context: Logging context
        """

        def _check_libreoffice():
            try:
                result = subprocess.run(
                    ["libreoffice", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                return result.returncode == 0
            except (
                subprocess.TimeoutExpired,
                FileNotFoundError,
                subprocess.SubprocessError,
            ):
                return False

        def _convert():
            # Optimized environment variables for LibreOffice
            env = os.environ.copy()
            env.update(
                {
                    "SAL_DEFAULT_PAPER": "A4",
                    "SAL_DISABLE_CUPS": "1",  # Disable CUPS to avoid printing issues
                    "HOME": os.path.dirname(docx_path),  # Set home to temp directory
                    "TMPDIR": os.path.dirname(docx_path),  # Use temp directory
                    "DISPLAY": ":99",  # Virtual display for headless mode
                }
            )

            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                docx_path,
            ]

            try:
                process = subprocess.run(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=True,
                )

                # Log all files in output directory for debugging
                output_dir = os.path.dirname(pdf_path)
                files_after = os.listdir(output_dir)
                logger.info(
                    f"Files in output directory after conversion: {files_after}",
                    extra=context,
                )

                return process.returncode == 0
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"LibreOffice conversion timed out after {self.timeout_seconds} seconds",
                    extra={**context, "event": "conversion_timeout"},
                )
                raise ConversionError(
                    "LibreOffice conversion timed out", context=context
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else 'Unknown error'}",
                    extra={
                        **context,
                        "event": "conversion_error",
                        "return_code": e.returncode,
                    },
                )
                raise ConversionError(
                    f"LibreOffice conversion failed: {e}", context=context
                )

        # Check LibreOffice availability
        loop = asyncio.get_event_loop()
        libreoffice_available = await loop.run_in_executor(None, _check_libreoffice)

        if not libreoffice_available:
            logger.error(
                "LibreOffice is not available",
                extra={**context, "event": "libreoffice_not_found"},
            )
            raise ConversionError(
                "LibreOffice is not installed or not available in PATH", context=context
            )

        # Perform conversion with retry logic
        logger.info(
            "Starting optimized LibreOffice conversion",
            extra={**context, "event": "conversion_start"},
        )

        for attempt in range(self.max_retries + 1):
            try:
                success = await loop.run_in_executor(None, _convert)
                if success:
                    logger.info(
                        f"LibreOffice conversion successful on attempt {attempt + 1}",
                        extra={
                            **context,
                            "event": "conversion_success",
                            "attempt": attempt + 1,
                        },
                    )
                    return
                else:
                    raise ConversionError(
                        "LibreOffice conversion returned non-zero exit code",
                        context=context,
                    )
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(
                        f"LibreOffice conversion failed after {self.max_retries + 1} attempts",
                        extra={
                            **context,
                            "event": "conversion_failed",
                            "attempts": self.max_retries + 1,
                        },
                    )
                    raise
                else:
                    logger.warning(
                        f"LibreOffice conversion attempt {attempt + 1} failed, retrying...",
                        extra={
                            **context,
                            "event": "conversion_retry",
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(1)  # Brief delay before retry


async def convert_word_to_pdf_optimized(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
    context: dict = None,
    is_celery_task: bool = False,
) -> tuple[str, str]:
    """
    Optimized Word to PDF conversion with parallel processing.

    Args:
        uploaded_file: Uploaded Word file
        suffix: Suffix for output filename
        context: Logging context

    Returns:
        Tuple of (input_docx_path, output_pdf_path)
    """
    converter = OptimizedWordToPDFConverter()
    return await converter.convert_word_to_pdf_optimized(
        uploaded_file=uploaded_file,
        suffix=suffix,
        context=context,
        is_celery_task=is_celery_task,
    )
