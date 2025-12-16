"""
API endpoint to cancel running Celery tasks.

This allows users to cancel long-running conversions if they close the page,
freeing up the queue for other users.
"""

from celery.result import AsyncResult
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status

from utils_site.celery import app as celery_app

from .logging_utils import get_logger

logger = get_logger(__name__)


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
        404: Task not found or already completed
    """
    try:
        import json

        data = json.loads(request.body)
        task_id = data.get("task_id")

        if not task_id:
            return JsonResponse(
                {"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get task result
        task_result = AsyncResult(task_id, app=celery_app)

        # Check if task exists and is active
        if task_result.state in ("PENDING", "PROGRESS", "STARTED"):
            # Revoke the task (terminate=True stops the worker immediately)
            # Note: This works best with Redis as broker (immediate termination)
            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

            logger.info(
                "Task cancelled by user",
                extra={"task_id": task_id, "state": task_result.state},
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Task cancelled successfully",
                    "task_id": task_id,
                },
                status=status.HTTP_200_OK,
            )

        elif task_result.state in ("SUCCESS", "FAILURE", "REVOKED"):
            # Task already completed or cancelled
            return JsonResponse(
                {
                    "status": "already_finished",
                    "message": f"Task already finished with state: {task_result.state}",
                    "task_id": task_id,
                },
                status=status.HTTP_200_OK,
            )

        else:
            return JsonResponse(
                {
                    "error": f"Task in unknown state: {task_result.state}",
                    "task_id": task_id,
                },
                status=status.HTTP_404_NOT_FOUND,
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
