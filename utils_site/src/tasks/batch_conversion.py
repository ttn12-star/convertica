"""Celery task for batch conversions (multiple files → ZIP).

Until 2026-07 every /batch/ endpoint converted files synchronously inside
the gunicorn request thread: a premium batch of 10 Word documents ran
LibreOffice in the web container (outside the worker memory budget) and
raced the Cloudflare 100 s edge timeout. This task moves the loop onto the
worker and reuses each batch view's own ``convert_single`` for per-tool
conversion logic, so sync and async batch behaviour cannot drift apart.
"""

import importlib
import os
import shutil
import time
import zipfile

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, EncryptedPDFError, InvalidPDFError
from src.tasks.pdf_conversion import _PeakRSSSampler, update_progress

logger = get_logger(__name__)


def _load_view_class(dotted: str):
    module_path, class_name = dotted.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)


def _mark_operation(task_id: str, **fields) -> None:
    """Best-effort OperationRun analytics update (mirrors generic task)."""
    try:
        from src.users.models import OperationRun

        OperationRun.objects.filter(task_id=task_id).update(**fields)
    except Exception as db_exc:
        logger.warning("OperationRun update failed for %s: %s", task_id, db_exc)


@shared_task(
    bind=True,
    name="batch.convert",
    # A batch is up to MAX_BATCH_FILES_PREMIUM (10) heavy conversions in one
    # task, so it gets its own generous limits instead of the global 8 min.
    soft_time_limit=1500,
    time_limit=1800,
    max_retries=0,
)
def batch_conversion_task(
    self,
    task_id: str,
    view_dotted: str,
    input_files: list[dict],
    params: dict,
    output_zip_filename: str,
    notify_user_id: int | None = None,
    notify_lang: str = "",
):
    """Convert ``input_files`` via the batch view's convert_single, zip results.

    Args:
        task_id: async task id; inputs live in MEDIA_ROOT/async_temp/<task_id>/
        view_dotted: dotted path of the BaseBatchAPIView subclass
        input_files: [{"path": ..., "name": <original upload name>}, ...]
        params: tool-specific POST params (already premium-validated in the view)
        output_zip_filename: user-facing ZIP name (view's OUTPUT_ZIP_FILENAME)
    """
    from django.core.files import File
    from django.utils import timezone

    started_ts = time.time()

    now = timezone.now()
    try:
        from src.users.models import OperationRun

        queued_at = (
            OperationRun.objects.filter(task_id=task_id)
            .values_list("queued_at", flat=True)
            .first()
        )
        queue_wait_ms = (
            int((now - queued_at).total_seconds() * 1000) if queued_at else None
        )
        _mark_operation(
            task_id, status="running", started_at=now, queue_wait_ms=queue_wait_ms
        )
    except Exception as db_exc:
        logger.warning("OperationRun 'running' update failed: %s", db_exc)

    peak_sampler = _PeakRSSSampler()
    peak_sampler.start()

    view = _load_view_class(view_dotted)()
    context = {"task_id": task_id, "batch_view": view_dotted}
    task_dir = os.path.dirname(input_files[0]["path"]) if input_files else None
    cleanup_dirs: set[str] = set()

    try:
        output_files: list[tuple[str, str]] = []
        failed_files: list[tuple[str, str]] = []
        all_failures_user_input = True
        total = len(input_files)

        for idx, entry in enumerate(input_files):
            update_progress(
                self,
                int(5 + (idx / max(total, 1)) * 85),
                f"Converting file {idx + 1}/{total}...",
            )
            name = entry["name"]
            try:
                with open(entry["path"], "rb") as fp:
                    uploaded = File(fp, name=name)
                    uploaded.content_type = ""  # match UploadedFile surface
                    cleanup_dir, output_path = view.convert_single(
                        uploaded, context, **params
                    )
                cleanup_dirs.add(cleanup_dir)
                output_files.append((name, output_path))
            except Exception as e:  # mirror the sync batch failure contract
                is_user_input = isinstance(e, EncryptedPDFError | InvalidPDFError)
                if not is_user_input:
                    all_failures_user_input = False
                log = logger.warning if is_user_input else logger.error
                log(
                    f"Batch item failed {name}: {e}",
                    extra={**context, "file_index": idx},
                )
                reason = (
                    str(e).strip()
                    if isinstance(e, ConversionError) and str(e).strip()
                    else "conversion failed"
                )
                failed_files.append((name or f"file_{idx + 1}", reason))

        if not output_files:
            raise ConversionError(
                "Failed to process any files"
                if all_failures_user_input
                else "Batch conversion failed"
            )

        update_progress(self, 92, "Packing archive...")
        zip_path = os.path.join(task_dir, output_zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for original_name, output_path in output_files:
                zipf.write(
                    output_path, view.get_zip_entry_name(original_name, output_path)
                )
            if failed_files:
                zipf.writestr(
                    "conversion_errors.txt",
                    "".join(f"{n}: {r}\n" for n, r in failed_files),
                )

        _mark_operation(
            task_id,
            status="success",
            finished_at=timezone.now(),
            duration_ms=int((time.time() - started_ts) * 1000),
            output_size=os.path.getsize(zip_path),
        )

        # Opt-in "email me the result" (set by the batch view layer).
        if notify_user_id:
            try:
                from src.tasks.email import send_conversion_result

                send_conversion_result.delay(
                    user_id=notify_user_id,
                    task_id=task_id,
                    output_path=zip_path,
                    output_filename=output_zip_filename,
                    lang=notify_lang,
                )
            except Exception as email_exc:
                logger.warning("result email enqueue failed, ignoring: %s", email_exc)

        # Web-push for batches sent to background (webhook/email pattern).
        try:
            from src.api.cancel_task_view import is_task_background

            if is_task_background(task_id):
                from src.tasks.push import send_conversion_ready
                from src.users.models import OperationRun

                push_user_id = (
                    OperationRun.objects.filter(task_id=task_id)
                    .values_list("user_id", flat=True)
                    .first()
                )
                if push_user_id:
                    send_conversion_ready.delay(
                        user_id=push_user_id,
                        task_id=task_id,
                        output_filename=output_zip_filename,
                        lang=notify_lang,
                    )
        except Exception as push_exc:
            logger.warning("push enqueue failed, ignoring: %s", push_exc)

        return {
            "output_path": zip_path,
            "output_filename": output_zip_filename,
            "batch_count": len(output_files),
            "batch_failed_count": len(failed_files),
        }

    except SoftTimeLimitExceeded:
        _mark_operation(
            task_id,
            status="error",
            finished_at=timezone.now(),
            duration_ms=int((time.time() - started_ts) * 1000),
            error_type="SoftTimeLimitExceeded",
        )
        raise
    except Exception as exc:
        _mark_operation(
            task_id,
            status="error",
            finished_at=timezone.now(),
            duration_ms=int((time.time() - started_ts) * 1000),
            error_type=type(exc).__name__,
        )
        raise
    finally:
        for d in cleanup_dirs:
            if d and os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        # Inputs are no longer needed once outputs are zipped (or the task
        # failed); the ZIP stays in task_dir for TaskResultAPIView. The
        # async_temp reaper sweeps the whole dir after expiry regardless.
        for entry in input_files:
            try:
                os.remove(entry["path"])
            except OSError:
                pass
        peak_sampler.stop()
        if peak_sampler.peak_mb is not None:
            _mark_operation(task_id, peak_rss_mb=peak_sampler.peak_mb)
