"""
PowerPoint to PDF conversion utilities using LibreOffice.

Converts PPT/PPTX files to PDF using LibreOffice headless mode.
Supports batch processing for premium users.
"""

import asyncio
import os
import subprocess
import tempfile

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, StorageError

logger = get_logger(__name__)

# Magic numbers for PowerPoint file validation
PPTX_MAGIC = b"PK\x03\x04"
PPT_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class PowerPointToPDFConverter:
    """PowerPoint to PDF converter with LibreOffice backend."""

    def __init__(self):
        self.timeout_seconds = (
            240  # 4 minutes timeout for LibreOffice (PPT can be complex)
        )
        self.max_retries = 2  # Maximum retry attempts

    async def convert_ppt_to_pdf(
        self,
        uploaded_file: UploadedFile,
        suffix: str = "_convertica",
        context: dict = None,
        is_celery_task: bool = False,
    ) -> tuple[str, str]:
        """
        Convert PowerPoint to PDF using LibreOffice.

        Args:
            uploaded_file: Uploaded PowerPoint file
            suffix: Suffix for output filename
            context: Logging context
            is_celery_task: Whether running in Celery task

        Returns:
            Tuple of (input_ppt_path, output_pdf_path)
        """
        if context is None:
            context = {}

        if is_celery_task:
            context["is_celery_task"] = True
            context["conversion_environment"] = "celery_worker"

        # Create temporary directory
        tmp_dir = tempfile.mkdtemp(prefix="ppt2pdf_")
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
            if not safe_name.lower().endswith((".ppt", ".pptx")):
                original_ext = os.path.splitext(original_filename)[1].lower()
                if original_ext in (".ppt", ".pptx"):
                    safe_name = os.path.splitext(safe_name)[0] + original_ext

            ppt_path = os.path.join(tmp_dir, safe_name)
            base_name, _ = os.path.splitext(safe_name)
            pdf_name = f"{base_name}{suffix}.pdf"
            pdf_path = os.path.join(tmp_dir, pdf_name)

            context.update(
                {
                    "ppt_path": ppt_path,
                    "pdf_path": pdf_path,
                    "input_filename": safe_name,
                    "original_filename": original_filename,
                    "input_size": uploaded_file.size,
                    "conversion_method": "libreoffice",
                }
            )

            # Save uploaded file
            await self._save_uploaded_file_async(uploaded_file, ppt_path, context)

            # Convert using LibreOffice
            await self._convert_with_libreoffice_async(ppt_path, pdf_path, context)

            # LibreOffice creates file as base_name.pdf, need to rename if suffix is used
            libreoffice_output = os.path.join(tmp_dir, f"{base_name}.pdf")
            if libreoffice_output != pdf_path and os.path.exists(libreoffice_output):
                os.rename(libreoffice_output, pdf_path)

            # Validate output
            if not os.path.exists(pdf_path):
                raise ConversionError(
                    "LibreOffice conversion failed - no output file generated",
                    context=context,
                )

            logger.info(
                "PowerPoint to PDF conversion completed successfully",
                extra={
                    **context,
                    "event": "ppt_to_pdf_success",
                    "output_size": os.path.getsize(pdf_path),
                },
            )

            return ppt_path, pdf_path

        except Exception as e:
            logger.error(
                f"PowerPoint to PDF conversion failed: {e}",
                extra={**context, "event": "ppt_to_pdf_error"},
                exc_info=True,
            )
            raise

    async def _save_uploaded_file_async(
        self, uploaded_file: UploadedFile, file_path: str, context: dict
    ) -> None:
        """Save uploaded file asynchronously."""
        loop = asyncio.get_event_loop()

        def _save_file():
            with open(file_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

        try:
            await loop.run_in_executor(None, _save_file)
            logger.debug(
                "PowerPoint file saved successfully",
                extra={**context, "event": "ppt_file_saved"},
            )
        except Exception as e:
            raise StorageError(f"Failed to save PowerPoint file: {e}", context=context)

    async def _convert_with_libreoffice_async(
        self, ppt_path: str, pdf_path: str, context: dict
    ) -> None:
        """Convert PowerPoint to PDF using LibreOffice with async execution."""
        loop = asyncio.get_event_loop()

        def _convert_with_libreoffice():
            """Perform LibreOffice conversion with retry logic."""
            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                ppt_path,
            ]

            # Optimized environment variables for LibreOffice
            env = os.environ.copy()
            env.update(
                {
                    "HOME": os.path.dirname(pdf_path),
                    "TMPDIR": os.path.dirname(pdf_path),
                    "LIBREOFFICE_USE_OPENGL": "true",
                }
            )

            logger.info(
                "Starting LibreOffice PowerPoint conversion",
                extra={
                    **context,
                    "event": "libreoffice_start",
                    "command": " ".join(cmd),
                },
            )

            try:
                result = subprocess.run(
                    cmd,
                    timeout=self.timeout_seconds,
                    capture_output=True,
                    text=True,
                    env=env,
                    check=True,
                )

                logger.info(
                    "LibreOffice conversion completed",
                    extra={
                        **context,
                        "event": "libreoffice_complete",
                        "return_code": result.returncode,
                        "stdout": result.stdout[:500] if result.stdout else "",
                    },
                )

            except subprocess.TimeoutExpired:
                logger.error(
                    f"LibreOffice conversion timed out after {self.timeout_seconds} seconds",
                    extra={**context, "event": "libreoffice_timeout"},
                )
                raise ConversionError(
                    "LibreOffice conversion timed out", context=context
                )

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"LibreOffice conversion failed with exit code {e.returncode}: {e.stderr}",
                    extra={
                        **context,
                        "event": "libreoffice_error",
                        "return_code": e.returncode,
                    },
                )
                raise ConversionError(
                    f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else 'Unknown error'}",
                    context=context,
                )

            except Exception as e:
                logger.error(
                    f"LibreOffice conversion failed: {e}",
                    extra={**context, "event": "libreoffice_exception"},
                )
                raise ConversionError(
                    f"LibreOffice conversion failed: {e}", context=context
                )

        # Check LibreOffice availability
        def _check_libreoffice():
            try:
                result = subprocess.run(
                    ["libreoffice", "--version"],
                    timeout=10,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.returncode == 0
            except Exception:
                return False

        libreoffice_available = await loop.run_in_executor(None, _check_libreoffice)

        if not libreoffice_available:
            logger.error(
                "LibreOffice is not available",
                extra={**context, "event": "libreoffice_not_found"},
            )
            raise ConversionError(
                "LibreOffice is not installed or not available in PATH", context=context
            )

        # Perform conversion with retries
        for attempt in range(self.max_retries + 1):
            try:
                await loop.run_in_executor(None, _convert_with_libreoffice)
                break  # Success, exit retry loop

            except ConversionError:
                if attempt == self.max_retries:
                    logger.error(
                        f"LibreOffice conversion failed after {self.max_retries + 1} attempts",
                        extra={**context, "event": "libreoffice_max_retries"},
                    )
                    raise

                logger.warning(
                    f"LibreOffice conversion attempt {attempt + 1} failed, retrying...",
                    extra={
                        **context,
                        "event": "libreoffice_retry",
                        "attempt": attempt + 1,
                    },
                )
                await asyncio.sleep(1)  # Brief delay before retry


# Global converter instance
_ppt_converter = PowerPointToPDFConverter()


def convert_ppt_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """
    Convert PowerPoint to PDF using LibreOffice.

    Args:
        uploaded_file: Uploaded PowerPoint file
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_ppt_path, output_pdf_path)
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _ppt_converter.convert_ppt_to_pdf(uploaded_file, suffix=suffix)
        )
    finally:
        loop.close()


def validate_ppt_file(uploaded_file: UploadedFile) -> tuple[bool, str | None]:
    """
    Validate PowerPoint file format.

    Args:
        uploaded_file: Uploaded file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not uploaded_file or not uploaded_file.name:
        return False, "No file provided"

    # Check file extension
    filename = uploaded_file.name.lower()
    if not filename.endswith((".ppt", ".pptx")):
        return False, "Invalid file extension. Only .ppt and .pptx files are supported"

    # Check file magic numbers
    try:
        file_data = uploaded_file.read(4)
        uploaded_file.seek(0)

        if filename.endswith(".pptx"):
            if not file_data.startswith(PPTX_MAGIC):
                return False, "Invalid PPTX file format"
        else:  # .ppt
            if not file_data.startswith(PPT_MAGIC):
                return False, "Invalid PPT file format"

    except Exception as e:
        logger.error(f"PowerPoint file validation error: {e}")
        return False, "Failed to validate PowerPoint file"

    return True, None
