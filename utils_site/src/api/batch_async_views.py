"""Async submission endpoint for batch conversions.

One generic route — ``<any-batch-route>/batch/async/`` — resolves the
corresponding synchronous ``BaseBatchAPIView`` subclass, runs the exact same
request-side validation (premium gate, per-file size/page caps, tool params),
saves the uploads into the async task dir and hands the conversion loop to
Celery. Status/result/cancel reuse the existing /api/tasks/ endpoints and
task tokens unchanged.

Why resolve-by-route instead of registering 29 async twins: parity is
automatic — any new batch tool gets an async endpoint for free, and the
validation logic physically cannot drift from the sync path.
"""

import os
import uuid

from django.http import HttpRequest
from django.urls import Resolver404, resolve
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .base_batch_views import BaseBatchAPIView
from .logging_utils import build_request_context, get_logger
from .operation_run_middleware_utils import ensure_request_id, normalize_conversion_type
from .premium_utils import can_use_batch_processing, is_premium_active
from .spam_protection import validate_spam_protection
from .task_tokens import create_task_token

logger = get_logger(__name__)


def _resolve_batch_view(batch_route: str) -> type[BaseBatchAPIView] | None:
    """Map ``<slug>/batch`` back to its registered sync batch view class."""
    try:
        match = resolve(f"/api/{batch_route}/")
    except Resolver404:
        return None
    view_cls = getattr(match.func, "cls", None) or getattr(
        match.func, "view_class", None
    )
    if view_cls is None or not issubclass(view_cls, BaseBatchAPIView):
        return None
    return view_cls


class BatchAsyncSubmitAPIView(APIView):
    """POST <slug>/batch/async/ → 202 {task_id, task_token}."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: HttpRequest, batch_route: str):
        from src.tasks.batch_conversion import batch_conversion_task

        spam_check = validate_spam_protection(request)
        if spam_check:
            return spam_check

        view_cls = _resolve_batch_view(batch_route)
        if view_cls is None:
            return Response(
                {"error": "Unknown batch endpoint"}, status=status.HTTP_404_NOT_FOUND
            )
        view = view_cls()

        files = request.FILES.getlist(view.FILE_FIELD_NAME)
        if not files:
            return Response(
                {
                    "error": f"No files provided. Use '{view.FILE_FIELD_NAME}' field name."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        can_batch, error_msg = can_use_batch_processing(request.user, len(files))
        if not can_batch:
            return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

        params = view.get_post_params(request)

        ocr_error = view.check_ocr_premium(request, params)
        if ocr_error is not None:
            return ocr_error

        # Same per-file premium/size/page validation the sync path applies —
        # done here in the web process so the user gets an immediate 4xx
        # instead of a queued task that fails later.
        for uploaded_file in files:
            limit_error = view.validate_premium_limits(uploaded_file, request)
            if limit_error is not None:
                return limit_error
            is_valid, err = view.validate_single(uploaded_file, params)
            if not is_valid:
                return Response(
                    {"error": err or "Invalid file"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Persist uploads into the shared async task dir for the worker.
        from .async_views import get_task_temp_dir

        task_id = str(uuid.uuid4())
        task_dir = get_task_temp_dir(task_id)
        input_files: list[dict] = []
        for idx, uploaded_file in enumerate(files):
            input_path = os.path.join(task_dir, f"input_{idx}")
            with open(input_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            input_files.append({"path": input_path, "name": uploaded_file.name})

        context = build_request_context(request)
        context["request_id"] = ensure_request_id(request)

        # Analytics row, mirroring AsyncConversionAPIView (best-effort).
        try:
            from django.utils import timezone
            from src.users.models import OperationRun

            OperationRun.objects.update_or_create(
                request_id=str(context.get("request_id") or ""),
                defaults={
                    "conversion_type": normalize_conversion_type(view.CONVERSION_TYPE),
                    "status": "queued",
                    "user": request.user if request.user.is_authenticated else None,
                    "is_premium": is_premium_active(request.user),
                    "task_id": task_id,
                    "input_size": sum(f.size for f in files),
                    "queued_at": timezone.now(),
                    "remote_addr": str(context.get("remote_addr") or ""),
                    "user_agent": str(context.get("user_agent") or ""),
                    "path": str(context.get("path") or ""),
                },
            )
        except Exception as db_exc:
            logger.warning("OperationRun 'queued' create failed: %s", db_exc)

        view_dotted = f"{view_cls.__module__}.{view_cls.__name__}"
        task_kwargs = {
            "task_id": task_id,
            "view_dotted": view_dotted,
            "input_files": input_files,
            "params": params,
            "output_zip_filename": view.OUTPUT_ZIP_FILENAME,
        }
        # Opt-in "email me the result" — batch is premium-only, so the only
        # gate needed is an authenticated user with an email on file.
        if (
            request.user.is_authenticated
            and getattr(request.user, "email", "")
            and str(request.data.get("email_result", "")).lower() in ("true", "1", "on")
        ):
            from django.utils import translation

            task_kwargs["notify_user_id"] = request.user.id
            task_kwargs["notify_lang"] = translation.get_language() or ""

        batch_conversion_task.apply_async(
            kwargs=task_kwargs,
            task_id=task_id,
            # Batch is a premium-only feature; route to the premium queue.
            queue="premium",
        )

        user_id = request.user.id if request.user.is_authenticated else None
        return Response(
            {
                "task_id": task_id,
                "task_token": create_task_token(task_id, user_id),
                "status": "PENDING",
                "message": f"Batch of {len(files)} files queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )
