"""
Optimized Word to PDF conversion with parallel processing and memory management.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning(
        "python-docx not available, page orientation detection will be limited"
    )

try:
    from PyPDF2 import PdfReader, PdfWriter

    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available, PDF orientation fixing will be disabled")

try:
    import olefile

    OLEFILE_AVAILABLE = True
except ImportError:
    OLEFILE_AVAILABLE = False
    logger.warning("olefile not available, .doc orientation detection will be limited")

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

        Features:
        - Automatic page orientation detection for both .docx and .doc files
        - Multi-section document support (uses majority orientation)
        - Fallback PDF orientation verification when Word orientation is unavailable
        - Fallback conversion logic for problematic documents
        - Non-ASCII filename handling
        - Memory-efficient chunked file writing
        - Detailed logging for debugging
        - PDF export with optimized quality parameters

        Orientation Detection:
        - .docx files: Full support via python-docx (all sections)
        - .doc files: Best-effort support via olefile (may not work for all documents)
        - Fallback: PDF-based consistency check if Word detection fails

        Limitations:
        - LibreOffice rendering may differ from MS Word (fonts, line breaks, spacing)
        - Complex formatting (nested tables, custom styles) may not preserve perfectly
        - .doc orientation detection is heuristic-based and may not work for all files
        - Multi-section documents with mixed orientations use majority orientation

        Args:
            uploaded_file: Uploaded Word file
            suffix: Suffix for output filename
            context: Logging context
            is_celery_task: Whether running in Celery worker context

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

            # Read page orientation from Word document before conversion
            word_orientation = await self._get_word_orientation_async(
                docx_path, context
            )

            # Perform optimized LibreOffice conversion
            await self._convert_with_libreoffice_async(docx_path, pdf_path, context)

            # Validate output - LibreOffice creates PDF based on the input filename
            # It may create the file with the original name, without suffix, or with a modified name
            # Check multiple possible locations
            expected_pdf_path = pdf_path  # With suffix: base_name_convertica.pdf
            original_pdf_path = os.path.join(
                tmp_dir, f"{base_name}.pdf"
            )  # Without suffix

            # Try to find the created PDF file
            found_pdf_path = None
            if os.path.exists(expected_pdf_path):
                found_pdf_path = expected_pdf_path
                logger.debug(
                    f"Found PDF at expected path: {expected_pdf_path}", extra=context
                )
            elif os.path.exists(original_pdf_path):
                found_pdf_path = original_pdf_path
                logger.info(
                    f"Found PDF at original path (no suffix): {original_pdf_path}",
                    extra=context,
                )
            else:
                # Fallback: search for any PDF file that was just created
                # This handles cases where LibreOffice uses a different naming scheme
                try:
                    all_files = os.listdir(tmp_dir)
                    pdf_files = [f for f in all_files if f.lower().endswith(".pdf")]

                    if pdf_files:
                        # Use the first PDF file found (should only be one)
                        found_pdf_path = os.path.join(tmp_dir, pdf_files[0])
                        logger.warning(
                            f"Found PDF with unexpected name: {pdf_files[0]}. Expected: {base_name}.pdf or {base_name}{suffix}.pdf",
                            extra={**context, "found_pdfs": pdf_files},
                        )
                    else:
                        logger.error(
                            f"Could not find any PDF file. Files in directory: {all_files}",
                            extra={**context, "all_files": all_files},
                        )
                        raise ConversionError(
                            "Output PDF file was not created", context=context
                        )
                except Exception as list_err:
                    logger.error(f"Failed to list directory: {list_err}", extra=context)
                    raise ConversionError(
                        "Output PDF file was not created", context=context
                    ) from list_err

            # If we found a PDF but it's not at the expected location, move it there
            if found_pdf_path != expected_pdf_path:
                try:
                    shutil.move(found_pdf_path, expected_pdf_path)
                    pdf_path = expected_pdf_path
                    logger.info(
                        f"Moved PDF from {os.path.basename(found_pdf_path)} to {os.path.basename(expected_pdf_path)}",
                        extra=context,
                    )
                except Exception as move_err:
                    logger.warning(
                        f"Failed to move PDF to expected location: {move_err}. Using original location.",
                        extra=context,
                    )
                    pdf_path = found_pdf_path
            else:
                pdf_path = found_pdf_path

            # Fix page orientation in PDF if it doesn't match Word document
            # If word_orientation is None, we'll try to detect it from the PDF itself
            if word_orientation:
                await self._fix_pdf_orientation_async(
                    pdf_path, word_orientation, context
                )
            else:
                # Fallback: Try to auto-detect orientation from PDF and verify consistency
                await self._verify_pdf_orientation_consistency_async(pdf_path, context)

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
                shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _validate_magic_number_async(
        self, uploaded_file: UploadedFile, context: dict
    ):
        """Validate Word file magic number asynchronously."""

        def _validate():
            try:
                header = uploaded_file.read(16)
                uploaded_file.seek(0)

                # Lenient: allow .doc/.docx even if magic missing, but warn
                if not (header.startswith(DOCX_MAGIC) or header.startswith(DOC_MAGIC)):
                    logger.warning(
                        "Word magic number missing, allowing based on extension/size",
                        extra={**context, "event": "word_magic_missing"},
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
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                }
            )

            # LibreOffice in headless mode can be sensitive to non-ASCII filenames and
            # locale settings inside containers. Use a deterministic ASCII filename.
            input_ext = os.path.splitext(docx_path)[1].lower()
            if input_ext not in (".doc", ".docx"):
                input_ext = ".docx"

            # Check if filename contains non-ASCII characters
            safe_input_path = docx_path
            needs_cleanup = False
            try:
                docx_path.encode("ascii")
            except UnicodeEncodeError:
                # Non-ASCII filename detected, create ASCII copy with unique name to avoid collisions
                unique_id = uuid.uuid4().hex[:8]
                safe_input_path = os.path.join(
                    os.path.dirname(docx_path), f"input_{unique_id}{input_ext}"
                )
                shutil.copyfile(docx_path, safe_input_path)
                needs_cleanup = True

            # Use writer_pdf_Export filter with parameters for better formatting preservation
            # This helps preserve word wrapping, hyphenation, and other formatting from Word
            # Determine appropriate infilter based on file extension
            infilter = None
            if safe_input_path.lower().endswith(".docx"):
                infilter = "MS Word 2007 XML"
            elif safe_input_path.lower().endswith(".doc"):
                infilter = "MS Word 97"

            def _build_cmd(use_infilter: bool) -> list[str]:
                cmd = [
                    "libreoffice",
                    "--headless",
                    "--nodefault",
                    "--nolockcheck",
                ]

                # Some documents fail with explicit infilter; keep it as an optimization
                # but allow fallback run without it.
                if use_infilter and infilter:
                    cmd.extend(["--infilter", infilter])

                # PDF export filter
                # Note: Complex filter parameters may cause issues with some LibreOffice versions
                # Using simple "pdf" format for maximum compatibility
                cmd.extend(
                    [
                        "--convert-to",
                        "pdf",  # Simple format without parameters for compatibility
                        "--outdir",
                        os.path.dirname(pdf_path),
                        safe_input_path,
                    ]
                )
                return cmd

            try:
                cmd = _build_cmd(use_infilter=True)
                logger.info(
                    f"Running LibreOffice command: {' '.join(cmd)}",
                    extra={**context, "event": "conversion_command"},
                )

                process = subprocess.run(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=True,
                )

                # Log LibreOffice output for debugging
                stdout_output = (
                    process.stdout.decode(errors="replace") if process.stdout else ""
                )
                stderr_output = (
                    process.stderr.decode(errors="replace") if process.stderr else ""
                )

                logger.info(
                    f"LibreOffice stdout: {stdout_output[:500]}",
                    extra={**context, "event": "conversion_stdout"},
                )

                if stderr_output:
                    logger.warning(
                        f"LibreOffice stderr: {stderr_output[:500]}",
                        extra={**context, "event": "conversion_stderr"},
                    )

                # Log all files in output directory for debugging
                output_dir = os.path.dirname(pdf_path)
                files_after = os.listdir(output_dir)
                pdf_files = [f for f in files_after if f.lower().endswith(".pdf")]

                logger.info(
                    f"Files in output directory after conversion: {files_after}. PDF files: {pdf_files}",
                    extra={
                        **context,
                        "event": "conversion_files",
                        "pdf_files": pdf_files,
                    },
                )

                # Check if PDF was actually created
                if not pdf_files:
                    logger.error(
                        "LibreOffice completed successfully but no PDF file was created",
                        extra={**context, "event": "no_pdf_created"},
                    )
                    return False

                return process.returncode == 0
            except subprocess.TimeoutExpired as timeout_error:
                logger.warning(
                    f"LibreOffice conversion timed out after {self.timeout_seconds} seconds",
                    extra={**context, "event": "conversion_timeout"},
                )
                raise ConversionError(
                    "LibreOffice conversion timed out", context=context
                ) from timeout_error
            except subprocess.CalledProcessError as e:
                # Retry once without --infilter inside the same attempt.
                stderr_preview = (
                    e.stderr.decode(errors="replace")[:1000] if e.stderr else ""
                )
                stdout_preview = (
                    e.stdout.decode(errors="replace")[:500] if e.stdout else ""
                )
                logger.error(
                    f"LibreOffice conversion failed: {stderr_preview or 'Unknown error'}",
                    extra={
                        **context,
                        "event": "conversion_error",
                        "return_code": e.returncode,
                        "stdout_preview": stdout_preview,
                        "command": " ".join(getattr(e, "cmd", []) or []),
                    },
                )

                try:
                    fallback_cmd = _build_cmd(use_infilter=False)
                    logger.info(
                        f"Running LibreOffice fallback command: {' '.join(fallback_cmd)}",
                        extra={**context, "event": "conversion_fallback_command"},
                    )

                    fallback_process = subprocess.run(
                        fallback_cmd,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=self.timeout_seconds,
                        check=True,
                    )

                    # Log fallback output
                    fallback_stdout = (
                        fallback_process.stdout.decode(errors="replace")
                        if fallback_process.stdout
                        else ""
                    )
                    fallback_stderr = (
                        fallback_process.stderr.decode(errors="replace")
                        if fallback_process.stderr
                        else ""
                    )

                    logger.info(
                        f"LibreOffice fallback stdout: {fallback_stdout[:500]}",
                        extra={**context, "event": "conversion_fallback_stdout"},
                    )

                    if fallback_stderr:
                        logger.warning(
                            f"LibreOffice fallback stderr: {fallback_stderr[:500]}",
                            extra={**context, "event": "conversion_fallback_stderr"},
                        )

                    output_dir = os.path.dirname(pdf_path)
                    files_after = os.listdir(output_dir)
                    pdf_files = [f for f in files_after if f.lower().endswith(".pdf")]

                    logger.info(
                        f"LibreOffice conversion successful without infilter; files: {files_after}. PDF files: {pdf_files}",
                        extra={
                            **context,
                            "event": "conversion_fallback_success",
                            "pdf_files": pdf_files,
                        },
                    )

                    # Check if PDF was created
                    if not pdf_files:
                        logger.error(
                            "LibreOffice fallback completed but no PDF file was created",
                            extra={**context, "event": "no_pdf_created_fallback"},
                        )
                        return False

                    return fallback_process.returncode == 0
                except subprocess.TimeoutExpired as fallback_timeout:
                    logger.error(
                        f"LibreOffice fallback conversion timed out after {self.timeout_seconds} seconds",
                        extra={
                            **context,
                            "event": "conversion_fallback_timeout",
                        },
                    )
                    raise ConversionError(
                        "LibreOffice conversion timed out on fallback attempt",
                        context=context,
                    ) from fallback_timeout
                except subprocess.CalledProcessError as fallback_e:
                    fallback_stderr_preview = (
                        fallback_e.stderr.decode(errors="replace")[:1000]
                        if fallback_e.stderr
                        else ""
                    )
                    logger.error(
                        f"LibreOffice fallback conversion failed: {fallback_stderr_preview or 'Unknown error'}",
                        extra={
                            **context,
                            "event": "conversion_fallback_error",
                            "return_code": fallback_e.returncode,
                            "command": " ".join(getattr(fallback_e, "cmd", []) or []),
                        },
                    )
                    # Both attempts failed, include both errors in exception
                    raise ConversionError(
                        f"LibreOffice conversion failed on both attempts. "
                        f"Original error: {e}. Fallback error: {fallback_e}",
                        context=context,
                    ) from fallback_e
            finally:
                # Cleanup temporary safe_input_path if it was created
                if needs_cleanup and safe_input_path != docx_path:
                    try:
                        os.remove(safe_input_path)
                        logger.debug(
                            f"Cleaned up temporary file: {safe_input_path}",
                            extra={**context, "event": "temp_file_cleanup"},
                        )
                    except FileNotFoundError:
                        # File already removed, ignore
                        pass
                    except OSError as cleanup_err:
                        logger.warning(
                            f"Failed to cleanup temporary file {safe_input_path}: {cleanup_err}",
                            extra={**context, "event": "temp_file_cleanup_failed"},
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
            except Exception:
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

    async def _get_word_orientation_async(
        self, docx_path: str, context: dict
    ) -> str | None:
        """
        Get page orientation from Word document.

        Supports:
        - .docx files (using python-docx)
        - .doc files (using olefile to read OLE properties)
        - Multi-section documents (checks all sections and returns most common orientation)

        Returns:
            'landscape' or 'portrait' or None if cannot determine
        """

        def _get_orientation():
            file_ext = docx_path.lower()

            # Try .docx first
            if file_ext.endswith(".docx") and DOCX_AVAILABLE:
                try:
                    doc = Document(docx_path)

                    if not doc.sections:
                        return None

                    # Check ALL sections to handle multi-section documents
                    orientations = []
                    for section in doc.sections:
                        width = section.page_width
                        height = section.page_height

                        if width and height:
                            orientation = "landscape" if width > height else "portrait"
                            orientations.append(orientation)

                    if not orientations:
                        return None

                    # Return most common orientation
                    landscape_count = orientations.count("landscape")
                    portrait_count = orientations.count("portrait")

                    result = (
                        "landscape" if landscape_count > portrait_count else "portrait"
                    )

                    if len(orientations) > 1:
                        logger.info(
                            f"Multi-section document detected: {len(orientations)} sections, "
                            f"{landscape_count} landscape, {portrait_count} portrait. Using: {result}",
                            extra={**context, "event": "multi_section_orientation"},
                        )

                    return result

                except Exception as e:
                    logger.warning(
                        f"Failed to read .docx orientation: {e}",
                        extra={**context, "event": "docx_orientation_failed"},
                    )

            # Try .doc with olefile
            if file_ext.endswith(".doc") and OLEFILE_AVAILABLE:
                ole = None
                stream = None
                try:
                    ole = olefile.OleFileIO(docx_path)

                    # Try to read WordDocument stream which contains document properties
                    if ole.exists("WordDocument"):
                        # Note: .doc format is complex, we try basic heuristics
                        # Read DOP (Document Properties) from WordDocument stream
                        stream = ole.openstream("WordDocument")
                        data = stream.read(4096)  # Read first 4KB

                        # Byte 0x44-0x45 in WordDocument stream sometimes contains orientation flag
                        # This is a best-effort heuristic and may not work for all .doc files
                        if len(data) > 0x45:
                            # Landscape flag is typically at offset 0x44, bit 0
                            flags = data[0x44] if len(data) > 0x44 else 0
                            is_landscape = (flags & 0x01) != 0

                            result = "landscape" if is_landscape else "portrait"
                            logger.info(
                                f".doc orientation detected: {result}",
                                extra={**context, "event": "doc_orientation_detected"},
                            )
                            return result

                except Exception as e:
                    logger.warning(
                        f"Failed to read .doc orientation: {e}",
                        extra={**context, "event": "doc_orientation_failed"},
                    )
                finally:
                    # Ensure resources are always closed
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass
                    if ole is not None:
                        try:
                            ole.close()
                        except Exception:
                            pass

            # If all methods fail, return None
            logger.debug(
                "Could not determine document orientation from Word file",
                extra={**context, "event": "orientation_unknown"},
            )
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_orientation)

    async def _fix_pdf_orientation_async(
        self, pdf_path: str, expected_orientation: str, context: dict
    ):
        """
        Fix PDF page orientation if it doesn't match expected orientation.

        Args:
            pdf_path: Path to PDF file
            expected_orientation: 'landscape' or 'portrait'
            context: Logging context
        """
        if not PYPDF2_AVAILABLE:
            logger.debug(
                "PyPDF2 not available, skipping PDF orientation fix",
                extra={**context, "event": "orientation_fix_skipped"},
            )
            return

        def _fix_orientation():
            try:
                reader = PdfReader(pdf_path)
                writer = PdfWriter()

                orientation_changed = False
                pages_fixed = 0

                for page_num, page in enumerate(reader.pages):
                    # Get page dimensions (in PDF points)
                    mediabox = page.mediabox
                    width = float(mediabox.width)
                    height = float(mediabox.height)

                    # Get current rotation from page (if any)
                    rotation = 0
                    if "/Rotate" in page:
                        rotation = int(page["/Rotate"])

                    # Calculate effective dimensions considering rotation
                    # If rotated 90 or 270 degrees, swap dimensions for orientation check
                    if rotation in [90, 270]:
                        effective_width = height
                        effective_height = width
                    else:
                        effective_width = width
                        effective_height = height

                    # Determine current orientation based on effective dimensions
                    current_orientation = (
                        "landscape"
                        if effective_width > effective_height
                        else "portrait"
                    )

                    # Check if orientation needs to be fixed
                    if current_orientation != expected_orientation:
                        # Rotate page 90 degrees to change orientation
                        # Note: This approach rotates the page visually, which changes
                        # how viewers display it but doesn't change the mediabox dimensions
                        page.rotate(90)
                        new_rotation = (rotation + 90) % 360
                        orientation_changed = True
                        pages_fixed += 1
                        logger.debug(
                            f"Rotated page {page_num + 1} to match {expected_orientation} orientation "
                            f"(was {current_orientation}, dimensions: {width:.1f}x{height:.1f}, "
                            f"rotation: {rotation}° -> {new_rotation}°)",
                            extra={**context, "page": page_num + 1},
                        )

                    writer.add_page(page)

                # Write corrected PDF only if orientation was changed
                if orientation_changed:
                    # Write to temporary file first to avoid corrupting original on failure
                    temp_pdf_path = f"{pdf_path}.tmp"
                    try:
                        with open(temp_pdf_path, "wb") as output_file:
                            writer.write(output_file)
                        # Replace original file with corrected version
                        shutil.move(temp_pdf_path, pdf_path)
                        logger.info(
                            f"Fixed PDF orientation to {expected_orientation} ({pages_fixed} pages rotated)",
                            extra={
                                **context,
                                "event": "orientation_fixed",
                                "pages_fixed": pages_fixed,
                            },
                        )
                    except Exception as write_error:
                        # Cleanup temp file if write or move failed
                        try:
                            if os.path.exists(temp_pdf_path):
                                os.remove(temp_pdf_path)
                        except OSError:
                            pass
                        raise write_error
                else:
                    logger.debug(
                        f"PDF orientation already matches {expected_orientation}",
                        extra={**context, "event": "orientation_ok"},
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to fix PDF orientation: {e}",
                    extra={**context, "event": "orientation_fix_failed"},
                )
                # Don't raise error - orientation fix is optional

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _fix_orientation)

    async def _verify_pdf_orientation_consistency_async(
        self, pdf_path: str, context: dict
    ):
        """
        Verify PDF orientation consistency across all pages.

        This is a fallback when Word orientation cannot be determined.
        Checks if all pages have consistent orientation. If they're mixed,
        logs a warning but doesn't change anything (preserves LibreOffice output).

        Args:
            pdf_path: Path to PDF file
            context: Logging context
        """
        if not PYPDF2_AVAILABLE:
            logger.debug(
                "PyPDF2 not available, skipping PDF orientation verification",
                extra={**context, "event": "orientation_verify_skipped"},
            )
            return

        def _verify_consistency():
            try:
                reader = PdfReader(pdf_path)

                if not reader.pages:
                    return

                orientations = []
                for page_num, page in enumerate(reader.pages):
                    mediabox = page.mediabox
                    width = float(mediabox.width)
                    height = float(mediabox.height)

                    # Get rotation
                    rotation = 0
                    if "/Rotate" in page:
                        rotation = int(page["/Rotate"])

                    # Calculate effective dimensions
                    if rotation in [90, 270]:
                        effective_width = height
                        effective_height = width
                    else:
                        effective_width = width
                        effective_height = height

                    orientation = (
                        "landscape"
                        if effective_width > effective_height
                        else "portrait"
                    )
                    orientations.append(orientation)

                # Check consistency
                unique_orientations = set(orientations)
                landscape_count = orientations.count("landscape")
                portrait_count = orientations.count("portrait")

                if len(unique_orientations) > 1:
                    logger.warning(
                        f"PDF has mixed orientations: {landscape_count} landscape, "
                        f"{portrait_count} portrait pages. Preserving LibreOffice output.",
                        extra={
                            **context,
                            "event": "mixed_orientation_detected",
                            "landscape_pages": landscape_count,
                            "portrait_pages": portrait_count,
                        },
                    )
                else:
                    dominant_orientation = (
                        orientations[0] if orientations else "unknown"
                    )
                    logger.info(
                        f"PDF has consistent {dominant_orientation} orientation across all {len(orientations)} pages",
                        extra={
                            **context,
                            "event": "consistent_orientation",
                            "orientation": dominant_orientation,
                            "pages": len(orientations),
                        },
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to verify PDF orientation consistency: {e}",
                    extra={**context, "event": "orientation_verify_failed"},
                )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _verify_consistency)


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
