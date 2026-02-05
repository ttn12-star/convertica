"""
API endpoint to cancel running Celery tasks.

This allows users to cancel long-running conversions if they close the page,
freeing up the queue for other users.
"""

import json

from celery.result import AsyncResult
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status

from utils_site.celery import app as celery_app

from .logging_utils import get_logger

logger = get_logger(__name__)

# Cache key prefix for cancelled tasks
CANCELLED_TASK_PREFIX = "cancelled_task:"
CANCELLED_TASK_TTL = 3600  # 1 hour TTL

# Cache key prefix for background tasks (premium)
BACKGROUND_TASK_PREFIX = "background_task:"
BACKGROUND_TASK_TTL = 3600  # 1 hour TTL (matches async temp file TTL)


def mark_task_cancelled(task_id: str) -> None:
    """Mark a task as cancelled in Redis cache."""
    cache.set(f"{CANCELLED_TASK_PREFIX}{task_id}", True, CANCELLED_TASK_TTL)


def is_task_cancelled(task_id: str) -> bool:
    """Check if a task has been cancelled."""
    return cache.get(f"{CANCELLED_TASK_PREFIX}{task_id}") is True


def clear_task_cancelled(task_id: str) -> None:
    """Clear the cancelled flag for a task."""
    cache.delete(f"{CANCELLED_TASK_PREFIX}{task_id}")


def mark_task_as_background(task_id: str) -> None:
    """Mark a task as a background task (premium)."""
    cache.set(f"{BACKGROUND_TASK_PREFIX}{task_id}", True, BACKGROUND_TASK_TTL)


def is_task_background(task_id: str) -> bool:
    """Check if a task is marked as background."""
    return cache.get(f"{BACKGROUND_TASK_PREFIX}{task_id}") is True


@csrf_exempt
@require_http_methods(["POST"])
def cancel_task(request):
    """
    Cancel a running Celery task.

    POST /api/cancel-task/
    Body: {"task_id": "abc-123-def"}

    Returns:
        200: Task cancelled successfully
        400: Missing or invalid task_id
    """
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")

        if not task_id:
            return JsonResponse(
                {"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get task result for logging
        task_result = AsyncResult(task_id, app=celery_app)
        current_state = task_result.state

        logger.info(
            "Attempting to cancel task",
            extra={
                "task_id": task_id,
                "state": current_state,
                "event": "task_cancel_attempt",
            },
        )

        # Always revoke - regardless of apparent state
        # Reason: AsyncResult.state is unreliable:
        # - "PENDING" can mean "in queue", "running", or "doesn't exist"
        # - State may not be updated in real-time
        #
        # Strategy:
        # 1. Mark as cancelled in Redis (persists across worker restarts)
        # 2. Revoke without terminate - marks in worker memory
        # 3. Revoke with terminate - kills if already running

        # Mark cancelled in Redis cache (survives worker restart)
        mark_task_cancelled(task_id)

        # Analytics (best-effort)
        try:
            from src.users.models import OperationRun

            OperationRun.objects.filter(task_id=task_id).exclude(
                status__in=["success", "error", "cancelled"]
            ).update(status="cancel_requested")
        except Exception:
            pass

        # Remove from queue (for pending tasks)
        celery_app.control.revoke(task_id, terminate=False)

        # Terminate running task (SIGTERM for graceful shutdown)
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")

        logger.info(
            "Task revoke commands sent",
            extra={
                "task_id": task_id,
                "previous_state": current_state,
                "event": "task_cancelled",
            },
        )

        # Check new state
        new_state = task_result.state

        return JsonResponse(
            {
                "status": "success",
                "message": "Task cancellation requested",
                "task_id": task_id,
                "previous_state": current_state,
                "current_state": new_state,
            },
            status=status.HTTP_200_OK,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON in request body"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["POST"])
def mark_operation_abandoned(request):
    """Mark an operation as abandoned (client closed/reloaded page).

    Expected JSON body: {"task_id": "..."} or {"request_id": "..."}
    This is intended to be called via navigator.sendBeacon().
    """
    try:
        data = json.loads(request.body or b"{}")
        task_id = data.get("task_id")
        request_id = data.get("request_id")

        if not task_id and not request_id:
            return JsonResponse(
                {"error": "task_id or request_id is required"}, status=400
            )

        try:
            from src.users.models import OperationRun

            qs = OperationRun.objects.exclude(
                status__in=["success", "error", "cancelled"]
            )
            if task_id:
                qs = qs.filter(task_id=task_id)
            if request_id:
                qs = qs.filter(request_id=request_id)
            qs.update(status="abandoned", finished_at=timezone.now())
        except Exception:
            pass

        return JsonResponse({"status": "ok"}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def mark_task_background(request):
    """Mark a task as a background task (premium users only).

    This tells the maintenance system not to clean up the task's temp files
    prematurely, and prevents auto-cancellation on page leave.

    POST /api/task-background/
    Body: {"task_id": "abc-123-def"}
    """
    try:
        # Only premium users can use background tasks
        if not request.user.is_authenticated or not getattr(
            request.user, "is_premium_active", False
        ):
            return JsonResponse({"error": "Premium subscription required"}, status=403)

        data = json.loads(request.body)
        task_id = data.get("task_id")

        if not task_id:
            return JsonResponse(
                {"error": "task_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mark_task_as_background(task_id)

        logger.info(
            "Task marked as background",
            extra={
                "task_id": task_id,
                "user_id": request.user.id,
                "event": "task_background",
            },
        )

        return JsonResponse(
            {"status": "success", "task_id": task_id},
            status=status.HTTP_200_OK,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error marking task as background: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)
