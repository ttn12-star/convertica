"""
Optimized Word to PDF conversion with parallel processing and memory management.
"""

import asyncio
import os
import shutil
import signal
import subprocess
import tempfile
import uuid
from collections.abc import Callable

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, InvalidPDFError, StorageError

logger = get_logger(__name__)


def _validate_output_pdf(pdf_path: str, context: dict | None = None) -> None:
    """Raise ConversionError if the produced PDF is empty, unreadable, or 0-page.

    LibreOffice can report success yet leave a truncated/partial PDF
    on disk; a bare ``size == 0`` check passes a 50-byte broken file. Confirm it
    opens and has at least one page so a corrupt result fails (and is retried)
    instead of being handed to the user.
    """
    if os.path.getsize(pdf_path) == 0:
        raise ConversionError("Output PDF file is empty", context=context)
    if PYPDF2_AVAILABLE:
        try:
            page_count = len(PdfReader(pdf_path).pages)
        except ConversionError:
            raise
        except Exception as exc:
            # Our output: no parser error in the chain (that would read as the
            # user's damaged file).
            raise ConversionError(
                f"Output PDF is invalid or truncated ({type(exc).__name__})",
                context=context,
            ) from None
        if page_count < 1:
            raise ConversionError("Output PDF has no pages", context=context)


def _run_libreoffice(
    cmd: list[str], env: dict, timeout: float
) -> subprocess.CompletedProcess:
    """Run a LibreOffice command, killing the whole process group on timeout.

    ``subprocess.run(timeout=...)`` kills only the direct child. LibreOffice
    forks a detached ``soffice.bin`` that survives that kill, holds the
    per-conversion ``UserInstallation`` profile lock, and makes subsequent
    conversions hang. Launching with ``start_new_session=True`` puts the whole
    LibreOffice process tree in its own group so a timeout can ``killpg`` it.

    Preserves ``subprocess.run(check=True)`` semantics: raises
    ``CalledProcessError`` on non-zero exit and ``TimeoutExpired`` on timeout
    (after the group has been killed and reaped).
    """
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()  # reap the (now-killed) process group
        raise
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=stdout, stderr=stderr
        )
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning(
        "python-docx not available, page orientation detection will be limited"
    )

try:
    from pypdf import PdfReader, PdfWriter

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


# writer_pdf_Export with explicit options (bookmarks, embedded standard fonts).
# Images as JPEG 90 at <=300 DPI: lossless kept PNG photos as Flate, a docx
# with three photos became a 37.8 MB PDF; now 2.5 MB, pixel difference ~1/255
# at 150 DPI, text identical. LibreOffice < 7.4 ignores these JSON options.
_WORD_PDF_FILTER = (
    "pdf:writer_pdf_Export:"
    "{"
    '"UseLosslessCompression":{"type":"boolean","value":"false"},'
    '"Quality":{"type":"long","value":"90"},'
    '"ReduceImageResolution":{"type":"boolean","value":"true"},'
    '"MaxImageResolution":{"type":"long","value":"300"},'
    '"ExportBookmarks":{"type":"boolean","value":"true"},'
    '"ExportNotes":{"type":"boolean","value":"false"},'
    '"EmbedStandardFonts":{"type":"boolean","value":"true"}'
    "}"
)


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
        check_cancelled: Callable[[], None] | None = None,
    ) -> tuple[str, str]:
        """
        Optimized Word to PDF conversion with advanced LibreOffice parameters.

        Features:
        - Advanced PDF export filters for better quality
        - Multiple fallback conversion strategies
        - Non-ASCII filename handling
        - Memory-efficient chunked file writing
        - Detailed logging for debugging
        - Automatic orientation handling by LibreOffice

        Limitations:
        - LibreOffice rendering may differ from MS Word (fonts, line breaks, spacing)
        - Complex formatting (nested tables, custom styles) may not preserve perfectly

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

        # On success the caller (sync/async view) still needs to stream the output
        # PDF, which lives inside tmp_dir — so we must NOT delete tmp_dir here on the
        # happy path (that left the returned pdf_path dangling → the view's
        # os.path.getsize 500'd). Mirror jpg_to_pdf: leave the dir for the caller to
        # stream and let the periodic reaper (cleanup_system_tmp sweeps the
        # "doc2pdf_opt_" prefix) reclaim it. Only clean up here on failure.
        conversion_succeeded = False

        try:
            if callable(check_cancelled):
                check_cancelled()

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

            # Save uploaded file
            await self._save_uploaded_file_async(
                uploaded_file, docx_path, context, check_cancelled=check_cancelled
            )

            # Magic bytes + OOXML structure before LibreOffice sees it: crafted
            # Office files are a recurring LibreOffice CVE surface.
            await self._validate_word_file_async(docx_path, context)

            # Perform optimized LibreOffice conversion
            # LibreOffice handles orientation correctly, no need for post-processing
            await self._convert_with_libreoffice_async(
                docx_path, pdf_path, context, check_cancelled=check_cancelled
            )

            if callable(check_cancelled):
                check_cancelled()

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

            # LibreOffice correctly handles orientation from Word documents —
            # trust its output. (A debug-only pypdf pass that re-read the whole
            # PDF just to log orientation stats was removed here: on big PDFs
            # it doubled the output I/O for zero user-visible effect.)

            # Log file size for debugging
            file_size = os.path.getsize(pdf_path)
            logger.info(f"PDF file created with size: {file_size} bytes", extra=context)

            _validate_output_pdf(pdf_path, context)

            logger.info(
                "Word to PDF conversion completed successfully",
                extra={**context, "event": "conversion_success"},
            )

            conversion_succeeded = True
            return docx_path, pdf_path

        finally:
            # Skip cleanup for Celery tasks (they handle it) and on the success path
            # (the caller streams pdf_path from tmp_dir; the reaper sweeps it later).
            # Only reclaim eagerly when the conversion failed.
            if (
                not is_celery_task
                and not conversion_succeeded
                and os.path.exists(tmp_dir)
            ):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _save_uploaded_file_async(
        self,
        uploaded_file: UploadedFile,
        docx_path: str,
        context: dict,
        check_cancelled: Callable[[], None] | None = None,
    ):
        """Save uploaded file asynchronously with controlled chunks."""

        def _save():
            try:
                with open(docx_path, "wb") as f:
                    for chunk in uploaded_file.chunks(chunk_size=self.chunk_size):
                        if callable(check_cancelled):
                            check_cancelled()
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
        self,
        docx_path: str,
        pdf_path: str,
        context: dict,
        check_cancelled: Callable[[], None] | None = None,
    ):
        """
        Perform LibreOffice conversion with optimization and retry logic.

        Args:
            docx_path: Path to input Word document
            pdf_path: Path to output PDF
            context: Logging context
        """
        if callable(check_cancelled):
            check_cancelled()

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

            # No --infilter: LibreOffice only accepts the --infilter=... form, so
            # the space-separated one made every first run exit 1 and the real
            # work happened in a second run. The correct form refuses .doc
            # files that are really RTF or .docx; content sniffing opens them.
            cmd = [
                "libreoffice",
                "--headless",
                "--nodefault",
                "--nolockcheck",
                "--convert-to",
                _WORD_PDF_FILTER,
                "--outdir",
                os.path.dirname(pdf_path),
                safe_input_path,
            ]
            output_dir = os.path.dirname(pdf_path)

            def _pdf_created() -> bool:
                return any(f.lower().endswith(".pdf") for f in os.listdir(output_dir))

            try:
                if callable(check_cancelled):
                    check_cancelled()
                logger.info(
                    f"Running LibreOffice command: {' '.join(cmd)}",
                    extra={**context, "event": "conversion_command"},
                )
                try:
                    _run_libreoffice(cmd, env, self.timeout_seconds)
                except subprocess.TimeoutExpired as e:
                    error = ConversionError(
                        f"LibreOffice conversion timed out after {self.timeout_seconds} seconds",
                        context=context,
                    )
                    # Same document, same hang: a retry only stacks another
                    # timeout on top, past the Celery and gunicorn limits.
                    error.retryable = False
                    raise error from e
                except subprocess.CalledProcessError as e:
                    stderr = (
                        e.stderr.decode(errors="replace")
                        if isinstance(e.stderr, bytes)
                        else e.stderr or ""
                    ).strip()
                    # soffice exits non-zero when it cannot start Java even
                    # though the PDF is fine.
                    _JAVA_WARNINGS = (
                        "failed to launch javaldx",
                        "java may not function",
                    )
                    if (
                        stderr
                        and all(w in stderr.lower() for w in _JAVA_WARNINGS)
                        and _pdf_created()
                    ):
                        return
                    oom = e.returncode in (137, -9)  # 137 via shell, -9 via Popen
                    error = ConversionError(
                        "LibreOffice conversion failed: "
                        + (
                            "the file is too large or complex to convert"
                            if oom
                            else stderr[:500] or f"exit code {e.returncode}"
                        ),
                        context=context,
                    )
                    # A retry re-runs the same allocation: two more OOM kills
                    # in a cgroup shared with the other workers.
                    error.retryable = not oom
                    raise error from e

                if not _pdf_created():
                    # LibreOffice exits 0 with no output when it cannot open the
                    # input. Retrying cannot fix the file, and it is the user's.
                    raise InvalidPDFError(
                        "The document could not be opened. It may be damaged or "
                        "not a real Word file.",
                        context=context,
                    )
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

        # LibreOffice availability: test PATH, not a live `soffice --version`.
        # That spawn raced the detached soffice.bin profile lock (see
        # _run_libreoffice) and timed out under load, aborting valid conversions
        # with a false "not installed". which() answers "is it in PATH" with no
        # process, lock, or timeout.
        loop = asyncio.get_event_loop()
        if shutil.which("libreoffice") is None:
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
            if callable(check_cancelled):
                check_cancelled()
            try:
                await loop.run_in_executor(None, _convert)
                logger.info(
                    f"LibreOffice conversion successful on attempt {attempt + 1}",
                    extra={
                        **context,
                        "event": "conversion_success",
                        "attempt": attempt + 1,
                    },
                )
                return
            except ConversionError as e:
                # Only a crashed soffice is worth another run. A file it cannot
                # open, an OOM kill or a timeout fails the same way every time.
                if isinstance(e, InvalidPDFError):
                    # The user's file, not our failure: no Sentry alert.
                    logger.warning(
                        f"LibreOffice could not open the document: {e}",
                        extra={**context, "event": "conversion_unopenable"},
                    )
                    raise
                if attempt == self.max_retries or not getattr(e, "retryable", True):
                    logger.error(
                        f"LibreOffice conversion failed after {attempt + 1} attempts: {e}",
                        extra={
                            **context,
                            "event": "conversion_failed",
                            "attempts": attempt + 1,
                        },
                    )
                    raise
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


async def convert_word_to_pdf_optimized(
    uploaded_file: UploadedFile,
    suffix: str = "_convertica",
    context: dict = None,
    is_celery_task: bool = False,
    check_cancelled: Callable[[], None] | None = None,
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
        check_cancelled=check_cancelled,
    )
