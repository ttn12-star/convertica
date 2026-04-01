"""
Celery tasks for PDF conversion operations.

These tasks handle heavy PDF conversion operations asynchronously
to prevent blocking the main request/response cycle and Cloudflare timeouts.

Tasks report progress via self.update_state() for real-time progress bars.
"""

import hashlib
import inspect
import os
import shutil
import time

from celery import shared_task
from celery.exceptions import Ignore, SoftTimeLimitExceeded
from django.core.files.base import File
from src.api.cancel_task_view import clear_task_cancelled, is_task_cancelled
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

# Conversion types that complete quickly (PDF-only, no LibreOffice).
# These are routed to the "fast" queue so they don't wait behind slow
# Word/Excel→PDF tasks in the "regular" queue.
FAST_CONVERSION_TYPES: frozenset[str] = frozenset(
    {
        "compress_pdf",
        "split_pdf",
        "merge_pdf",
        "rotate_pdf",
        "crop_pdf",
        "add_watermark",
        "add_page_numbers",
        "organize_pdf",
        "extract_pages",
        "remove_pages",
        "jpg_to_pdf",
        "pdf_to_jpg",
    }
)

# Maximum output file size (bytes) eligible for SHA-256 result caching.
# Large files are not cached to avoid filling Redis.
_CACHE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_CACHE_TTL = 86400  # 24 hours


def _sha256_file(path: str) -> str:
    """Return the hex SHA-256 digest of a file without loading it fully into RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_key(sha256: str, conversion_type: str, kwargs: dict) -> str:
    """Stable cache key for a given input file + operation + parameters."""
    # Exclude internal/runtime kwargs that don't affect the output.
    excluded = {"suffix", "is_celery_task", "context", "check_cancelled", "is_premium"}
    stable = {k: v for k, v in sorted(kwargs.items()) if k not in excluded}
    params_hash = hashlib.md5(str(stable).encode()).hexdigest()[:8]
    return f"conv_cache:{conversion_type}:{sha256}:{params_hash}"


class TaskCancelledException(Exception):
    """Raised when a task has been cancelled by the user."""


def check_task_cancelled(task_id: str) -> None:
    """Check if task was cancelled and raise exception if so."""
    if is_task_cancelled(task_id):
        logger.info(f"Task {task_id} was cancelled by user, stopping execution")
        raise TaskCancelledException(f"Task {task_id} cancelled by user")


def update_progress(task, progress: int, current_step: str = "", total_steps: int = 0):
    """Helper to update task progress."""
    task.update_state(
        state="PROGRESS",
        meta={
            "progress": progress,
            "current_step": current_step,
            "total_steps": total_steps,
        },
    )


@shared_task(
    bind=True,
    name="pdf_conversion.generic_conversion",
    queue=lambda self, task_id, input_path, original_filename, conversion_type, **kwargs: (
        "premium" if kwargs.get("is_premium", False) else "regular"
    ),
    soft_time_limit=420,  # 7 minutes soft limit (reduced for 4GB server)
    time_limit=480,  # 8 minutes hard limit (reduced for 4GB server)
    acks_late=True,  # Acknowledge after completion (allows task revocation)
    reject_on_worker_lost=True,  # Don't requeue if worker dies
)
def generic_conversion_task(
    self,
    task_id: str,
    input_path: str,
    original_filename: str,
    conversion_type: str,
    **kwargs,
) -> dict:
    """
    Universal async conversion task with progress reporting.

    Supports all conversion types by dynamically importing the converter.

    Args:
        task_id: Unique task identifier
        input_path: Path to the uploaded file
        original_filename: Original filename for output naming
        conversion_type: Type of conversion (e.g., 'pdf_to_word', 'word_to_pdf')
        **kwargs: Additional conversion parameters

    Returns:
        dict: Result containing output_path and output_filename
    """
    task_dir = os.path.dirname(input_path)
    output_path = None
    # Use the task_id parameter (same as self.request.id, but explicit)
    # This is what the frontend uses to cancel
    cancellation_id = task_id
    input_fp = None

    started_ts = time.time()

    # Mark task as running in analytics (best-effort)
    try:
        from django.utils import timezone
        from src.users.models import OperationRun

        now = timezone.now()
        queued_at = (
            OperationRun.objects.filter(task_id=cancellation_id)
            .values_list("queued_at", flat=True)
            .first()
        )
        queue_wait_ms = None
        if queued_at:
            queue_wait_ms = int((now - queued_at).total_seconds() * 1000)
        OperationRun.objects.filter(task_id=cancellation_id).update(
            status="running",
            started_at=now,
            queue_wait_ms=queue_wait_ms,
        )
    except Exception:
        pass

    try:
        # Check cancellation before starting
        check_task_cancelled(cancellation_id)

        # Step 1: Validate input file exists
        update_progress(self, 5, "Validating input file...", 5)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Check cancellation before loading file
        check_task_cancelled(cancellation_id)

        # Step 2: Load the file
        update_progress(self, 15, "Loading file...", 5)

        input_fp = open(input_path, "rb")
        try:
            uploaded_file = File(input_fp, name=original_filename)
        except Exception:
            input_fp.close()
            input_fp = None
            raise

        # --- SHA-256 result cache (idempotent operations only) ---
        # For FAST_CONVERSION_TYPES we check if an identical file+params combo
        # was already converted recently and serve the cached output directly.
        # Only small outputs (<5 MB) are cached to avoid bloating Redis.
        cached_output: bytes | None = None
        cache_key_str: str | None = None
        if conversion_type in FAST_CONVERSION_TYPES:
            try:
                from django.core.cache import cache as django_cache

                file_sha256 = _sha256_file(input_path)
                cache_key_str = _cache_key(file_sha256, conversion_type, kwargs)
                cached_output = django_cache.get(cache_key_str)
                if cached_output is not None:
                    logger.info(
                        f"Cache hit for {conversion_type} (sha256={file_sha256[:12]}…)",
                        extra={"event": "conversion_cache_hit"},
                    )
            except Exception as cache_exc:
                logger.debug(f"Cache lookup skipped: {cache_exc}")
                cached_output = None

        if cached_output is not None:
            # Write cached bytes to the task output directory and return.
            import mimetypes

            base_name = os.path.splitext(original_filename)[0]
            ext_map = {
                "pdf_to_jpg": ".zip",
                "jpg_to_pdf": ".pdf",
            }
            out_ext = ext_map.get(conversion_type, ".pdf")
            output_filename = f"{base_name}_convertica{out_ext}"
            final_output_path = os.path.join(task_dir, output_filename)
            with open(final_output_path, "wb") as fh:
                fh.write(cached_output)
            update_progress(self, 100, "Complete!", 5)
            clear_task_cancelled(cancellation_id)
            logger.info(f"Served {conversion_type} from cache: {final_output_path}")
            # Record analytics
            try:
                from django.utils import timezone
                from src.users.models import OperationRun

                now = timezone.now()
                duration_ms = int((time.time() - started_ts) * 1000)
                OperationRun.objects.filter(task_id=cancellation_id).update(
                    status="success",
                    finished_at=now,
                    duration_ms=duration_ms,
                    output_size=len(cached_output),
                )
            except Exception:
                pass
            return {
                "status": "success",
                "output_path": final_output_path,
                "output_filename": output_filename,
                "conversion_type": conversion_type,
            }

        # Step 3: Get the converter function based on conversion type
        update_progress(self, 25, "Preparing conversion...", 5)

        converter_map = {
            "pdf_to_word": (
                "src.api.pdf_convert.pdf_to_word_optimized",
                "convert_pdf_to_docx_optimized",
            ),
            "word_to_pdf": (
                "src.api.optimization_manager",
                "convert_word_to_pdf",
            ),
            "pdf_to_excel": (
                "src.api.pdf_convert.pdf_to_excel.utils",
                "convert_pdf_to_excel",
            ),
            "pdf_to_jpg": (
                "src.api.optimization_manager",
                "convert_pdf_to_jpg",
            ),
            "jpg_to_pdf": (
                "src.api.pdf_convert.jpg_to_pdf.utils",
                "convert_jpg_to_pdf",
            ),
            "epub_to_pdf": (
                "src.api.epub_convert.utils",
                "convert_epub_to_pdf",
            ),
            "pdf_to_epub": (
                "src.api.epub_convert.utils",
                "convert_pdf_to_epub",
            ),
            "pdf_to_markdown": (
                "src.api.pdf_convert.pdf_to_markdown.utils",
                "convert_pdf_to_markdown",
            ),
            "compress_pdf": ("src.api.pdf_organize.compress_pdf.utils", "compress_pdf"),
            "merge_pdf": ("src.api.pdf_organize.merge_pdf.utils", "merge_pdfs"),
            "split_pdf": ("src.api.pdf_organize.split_pdf.utils", "split_pdf"),
            "rotate_pdf": ("src.api.pdf_edit.rotate_pdf.utils", "rotate_pdf"),
            "add_watermark": ("src.api.pdf_edit.add_watermark.utils", "add_watermark"),
            "crop_pdf": ("src.api.pdf_edit.crop_pdf.utils", "crop_pdf"),
            "add_page_numbers": (
                "src.api.pdf_edit.add_page_numbers.utils",
                "add_page_numbers",
            ),
            "organize_pdf": ("src.api.pdf_organize.organize_pdf.utils", "organize_pdf"),
            "extract_pages": (
                "src.api.pdf_organize.extract_pages.utils",
                "extract_pages",
            ),
            "remove_pages": ("src.api.pdf_organize.remove_pages.utils", "remove_pages"),
        }

        if conversion_type not in converter_map:
            raise ValueError(f"Unknown conversion type: {conversion_type}")

        module_path, func_name = converter_map[conversion_type]

        # Dynamic import
        import importlib

        module = importlib.import_module(module_path)
        converter_func = getattr(module, func_name)

        # Check cancellation before heavy conversion
        check_task_cancelled(cancellation_id)

        # Step 4: Perform conversion
        update_progress(self, 35, "Converting file...", 60)

        # Prepare kwargs (merge request-provided kwargs with task-internal kwargs)
        conversion_kwargs: dict = {
            **kwargs,
            "suffix": "_convertica",
            "is_celery_task": True,
            "context": {},
            "check_cancelled": lambda: check_task_cancelled(cancellation_id),
        }

        def _filter_kwargs_for_callable(func, provided_kwargs: dict) -> dict:
            sig = inspect.signature(func)
            params = sig.parameters
            accepts_var_kw = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
            )
            if accepts_var_kw:
                return provided_kwargs
            return {k: v for k, v in provided_kwargs.items() if k in params}

        filtered_kwargs = _filter_kwargs_for_callable(converter_func, conversion_kwargs)

        # Call converter function
        if conversion_type == "pdf_to_word":
            # Handle async function for pdf_to_word
            import asyncio

            # Generate output filename first
            output_filename = (
                f"{os.path.splitext(original_filename)[0]}_convertica.docx"
            )
            final_output_path = os.path.join(task_dir, output_filename)

            # Pass output_path and progress update function to converter
            filtered_kwargs.update(
                _filter_kwargs_for_callable(
                    converter_func,
                    {
                        "output_path": final_output_path,
                        "update_progress": lambda progress, step: update_progress(
                            self, progress, step, 60
                        ),
                    },
                )
            )

            _, _ = asyncio.run(converter_func(uploaded_file, **filtered_kwargs))

            # File should already be copied by converter
            if os.path.exists(final_output_path):
                output_path = final_output_path
            else:
                raise FileNotFoundError(f"Output file not found: {final_output_path}")
        elif conversion_type == "word_to_pdf":
            # Handle async function for word_to_pdf
            import asyncio

            if inspect.iscoroutinefunction(converter_func):
                # Handle async function
                result = asyncio.run(converter_func(uploaded_file, **filtered_kwargs))
                if isinstance(result, tuple) and len(result) == 2:
                    # For word_to_pdf, result is (docx_path, pdf_path) - we want pdf_path
                    _, output_path = result
                else:
                    output_path = result
            else:
                # Handle sync function
                result = converter_func(uploaded_file, **filtered_kwargs)
                if isinstance(result, tuple) and len(result) == 2:
                    # For word_to_pdf, result is (docx_path, pdf_path) - we want pdf_path
                    _, output_path = result
                else:
                    output_path = result
        else:
            # Handle other converters (check if async)
            import asyncio

            if inspect.iscoroutinefunction(converter_func):
                # Handle async function
                result = asyncio.run(converter_func(uploaded_file, **filtered_kwargs))
                if isinstance(result, tuple) and len(result) == 2:
                    _, output_path = result
                else:
                    output_path = result
            else:
                # Handle sync function
                result = converter_func(uploaded_file, **filtered_kwargs)
                if isinstance(result, tuple) and len(result) == 2:
                    _, output_path = result
                else:
                    output_path = result

        # Step 5: Move output to task directory for persistence
        update_progress(self, 85, "Finalizing...", 5)

        # For non-pdf_to_word conversions, handle file copying
        if conversion_type != "pdf_to_word":
            # Generate output filename
            base_name = os.path.splitext(original_filename)[0]
            output_ext = os.path.splitext(output_path)[1]

            # Map conversion types to output extensions
            ext_map = {
                "pdf_to_jpg": ".zip",
                "word_to_pdf": ".pdf",
                "jpg_to_pdf": ".pdf",
            }
            if conversion_type in ext_map:
                output_ext = ext_map[conversion_type]

            output_filename = f"{base_name}_convertica{output_ext}"
            final_output_path = os.path.join(task_dir, output_filename)

            # Move or copy output to task dir
            if output_path != final_output_path:
                if os.path.exists(output_path):
                    shutil.copy2(output_path, final_output_path)
                    # Cleanup original temp file
                    try:
                        os.remove(output_path)
                    except OSError as e:
                        logger.warning(
                            "Failed to cleanup temp file %s: %s", output_path, e
                        )
                else:
                    raise FileNotFoundError(f"Output file not found: {output_path}")
        else:
            # For pdf_to_word, final_output_path is already set
            final_output_path = output_path

        update_progress(self, 100, "Complete!", 5)

        # --- Store result in SHA-256 cache for future identical requests ---
        if cache_key_str is not None and conversion_type in FAST_CONVERSION_TYPES:
            try:
                out_size = os.path.getsize(final_output_path)
                if out_size <= _CACHE_MAX_BYTES:
                    from django.core.cache import cache as django_cache

                    with open(final_output_path, "rb") as fh:
                        django_cache.set(cache_key_str, fh.read(), timeout=_CACHE_TTL)
                    logger.debug(
                        f"Cached {conversion_type} result ({out_size} bytes, ttl={_CACHE_TTL}s)",
                        extra={"event": "conversion_cache_store"},
                    )
            except Exception as cache_exc:
                logger.debug(f"Cache store skipped: {cache_exc}")

        # Clear cancelled flag if task completed successfully
        clear_task_cancelled(cancellation_id)

        logger.info(f"Conversion {conversion_type} completed: {final_output_path}")

        # Analytics success (best-effort)
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            now = timezone.now()
            duration_ms = int((time.time() - started_ts) * 1000)
            out_size = None
            try:
                out_size = os.path.getsize(final_output_path)
            except Exception:
                pass
            OperationRun.objects.filter(task_id=cancellation_id).update(
                status="success",
                finished_at=now,
                duration_ms=duration_ms,
                output_size=out_size,
            )
        except Exception:
            pass

        return {
            "status": "success",
            "output_path": final_output_path,
            "output_filename": output_filename,
            "conversion_type": conversion_type,
        }

    except TaskCancelledException:
        # Task was cancelled by user - cleanup and exit gracefully
        logger.info(f"Task {cancellation_id} cancelled, cleaning up")
        try:
            if task_dir and os.path.isdir(task_dir):
                shutil.rmtree(task_dir, ignore_errors=True)
        except Exception:
            pass
        # Use Ignore to not record as failure
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            now = timezone.now()
            duration_ms = int((time.time() - started_ts) * 1000)
            OperationRun.objects.filter(task_id=cancellation_id).update(
                status="cancelled",
                finished_at=now,
                duration_ms=duration_ms,
            )
        except Exception:
            pass
        raise Ignore()

    except SoftTimeLimitExceeded:
        # Task exceeded soft time limit - check if it was user cancellation
        logger.warning(
            f"Task {cancellation_id} exceeded soft time limit",
            extra={"conversion_type": conversion_type},
        )

        # Check if this was due to user cancellation
        if is_task_cancelled(cancellation_id):
            logger.info(
                f"Task {cancellation_id} cancelled during conversion, cleaning up"
            )
            try:
                if task_dir and os.path.isdir(task_dir):
                    shutil.rmtree(task_dir, ignore_errors=True)
            except Exception:
                pass
            try:
                from django.utils import timezone
                from src.users.models import OperationRun

                now = timezone.now()
                duration_ms = int((time.time() - started_ts) * 1000)
                OperationRun.objects.filter(task_id=cancellation_id).update(
                    status="cancelled",
                    finished_at=now,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass
            raise Ignore()

        # Record timeout as error (best-effort)
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            now = timezone.now()
            duration_ms = int((time.time() - started_ts) * 1000)
            OperationRun.objects.filter(task_id=cancellation_id).update(
                status="error",
                finished_at=now,
                duration_ms=duration_ms,
                error_type="SoftTimeLimitExceeded",
                error_message="Task exceeded time limit",
            )
        except Exception:
            pass

        return {
            "status": "error",
            "error": "Task exceeded time limit",
            "conversion_type": conversion_type,
        }

    except Exception as exc:
        logger.error(f"Conversion {conversion_type} failed: {str(exc)}", exc_info=True)

        # Analytics error (best-effort)
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            now = timezone.now()
            duration_ms = int((time.time() - started_ts) * 1000)
            OperationRun.objects.filter(task_id=cancellation_id).update(
                status="error",
                finished_at=now,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc)[:2000],
            )
        except Exception:
            pass

        # Don't retry for user errors (validation, etc.) or permanent PDF corruption
        error_message = str(exc)
        exc_type = type(exc).__name__

        # Check for permanent PDF corruption errors (PyMuPDF xref/object errors)
        is_permanent_corruption = (
            "object out of range" in error_message.lower()
            or "xref" in error_message.lower()
            or "FzErrorFormat" in exc_type
        )

        if is_permanent_corruption:
            return {
                "status": "error",
                "error": (
                    "PDF file is corrupted or has structural errors. "
                    "Please try re-saving the PDF (Print to PDF) or repairing it with a PDF tool, then retry."
                ),
                "conversion_type": conversion_type,
            }

        if any(
            msg in error_message.lower()
            for msg in [
                "invalid",
                "corrupt",
                "password",
                "encrypted",
                "not found",
                "not a valid image",
                "please upload",
            ]
        ):
            return {
                "status": "error",
                "error": error_message,
                "conversion_type": conversion_type,
            }

        # Retry for transient errors
        raise self.retry(exc=exc, countdown=30, max_retries=2)

    finally:
        try:
            if input_fp is not None:
                input_fp.close()
        except Exception:
            pass


# Legacy tasks for backwards compatibility - updated to use new queues
@shared_task(bind=True, name="pdf_conversion.convert_pdf_to_word", queue="regular")
def convert_pdf_to_word_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        self,
        task_id=self.request.id,
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="pdf_to_word",
        **kwargs,
    )


@shared_task(bind=True, name="pdf_conversion.convert_word_to_pdf", queue="regular")
def convert_word_to_pdf_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        self,
        task_id=self.request.id,
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="word_to_pdf",
        **kwargs,
    )


@shared_task(bind=True, name="pdf_conversion.compress_pdf", queue="regular")
def compress_pdf_task(
    self,
    file_path: str,
    output_filename: str,
    compression_level: str = "medium",
    **kwargs,
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        self,
        task_id=self.request.id,
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="compress_pdf",
        compression_level=compression_level,
        **kwargs,
    )
