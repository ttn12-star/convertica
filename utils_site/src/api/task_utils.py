"""
Task utilities for Celery task management.

Provides helper functions for routing tasks to appropriate queues
based on user premium status and task priority.
"""


def get_task_queue(is_premium: bool = False) -> str:
    """Get appropriate Celery queue based on user premium status.

    Args:
        is_premium: Whether user has premium subscription

    Returns:
        Queue name ('premium' or 'regular')
    """
    return "premium" if is_premium else "regular"


def get_task_priority(is_premium: bool = False) -> int:
    """Get task priority based on user premium status.

    Args:
        is_premium: Whether user has premium subscription

    Returns:
        Priority value (9 for premium, 5 for regular)
    """
    return 9 if is_premium else 5


def apply_task_options(
    task_kwargs: dict,
    is_premium: bool = False,
    queue: str | None = None,
    priority: int | None = None,
) -> dict:
    """Apply task routing options based on user premium status.

    Args:
        task_kwargs: Base task kwargs
        is_premium: Whether user has premium subscription
        queue: Override queue (optional)
        priority: Override priority (optional)

    Returns:
        Updated task kwargs with queue and priority
    """
    task_kwargs = task_kwargs.copy()

    # Set queue
    if queue:
        task_kwargs["queue"] = queue
    else:
        task_kwargs["queue"] = get_task_queue(is_premium)

    # Set priority
    if priority is not None:
        task_kwargs["priority"] = priority
    else:
        task_kwargs["priority"] = get_task_priority(is_premium)

    return task_kwargs
