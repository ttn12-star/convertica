"""
WebSocket utility functions for sending progress updates.
Provides helper functions to send real-time updates via Django Channels.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def send_conversion_progress(task_id, progress, message, status="processing"):
    """
    Send conversion progress update via WebSocket.

    Args:
        task_id: Unique task identifier
        progress: Progress percentage (0-100)
        message: Progress message to display
        status: Status string (processing, completed, error)

    Example:
        send_conversion_progress('task-123', 45, 'Converting page 5 of 10...', 'processing')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.warning("Channel layer not configured. WebSocket updates disabled.")
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"conversion_{task_id}",
            {
                "type": "conversion_progress",
                "progress": progress,
                "message": message,
                "status": status,
            },
        )
        logger.debug(f"Progress sent: task_id={task_id}, progress={progress}%")
    except Exception as e:
        logger.error(f"Failed to send progress update: {e}")


def send_conversion_completed(
    task_id, download_url, filename, file_size=None, message="Conversion completed"
):
    """
    Send conversion completion notification via WebSocket.

    Args:
        task_id: Unique task identifier
        download_url: URL to download converted file
        filename: Name of converted file
        file_size: Size of converted file in bytes (optional)
        message: Completion message

    Example:
        send_conversion_completed('task-123', '/media/converted/file.docx', 'document.docx', 245760)
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"conversion_{task_id}",
            {
                "type": "conversion_completed",
                "download_url": download_url,
                "filename": filename,
                "file_size": file_size,
                "message": message,
            },
        )
        logger.info(f"Completion sent: task_id={task_id}, filename={filename}")
    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")


def send_conversion_error(task_id, error_message, error_details=None):
    """
    Send conversion error notification via WebSocket.

    Args:
        task_id: Unique task identifier
        error_message: User-friendly error message
        error_details: Technical error details (optional)

    Example:
        send_conversion_error('task-123', 'Failed to convert PDF', 'Invalid PDF structure')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"conversion_{task_id}",
            {
                "type": "conversion_error",
                "message": error_message,
                "error": error_details or error_message,
            },
        )
        logger.error(f"Error sent: task_id={task_id}, error={error_message}")
    except Exception as e:
        logger.error(f"Failed to send error notification: {e}")


def send_batch_progress(
    batch_id,
    total_files,
    completed_files,
    current_file,
    progress,
    message,
    status="processing",
):
    """
    Send batch conversion progress update via WebSocket.

    Args:
        batch_id: Unique batch identifier
        total_files: Total number of files in batch
        completed_files: Number of completed files
        current_file: Name of currently processing file
        progress: Overall progress percentage (0-100)
        message: Progress message
        status: Status string

    Example:
        send_batch_progress('batch-456', 10, 5, 'document5.pdf', 50, 'Processing file 5 of 10...', 'processing')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"batch_{batch_id}",
            {
                "type": "batch_progress",
                "total_files": total_files,
                "completed_files": completed_files,
                "current_file": current_file,
                "progress": progress,
                "message": message,
                "status": status,
            },
        )
        logger.debug(
            f"Batch progress sent: batch_id={batch_id}, {completed_files}/{total_files}"
        )
    except Exception as e:
        logger.error(f"Failed to send batch progress: {e}")


def send_batch_file_completed(batch_id, filename, file_index, message="File completed"):
    """
    Send notification when individual file in batch is completed.

    Args:
        batch_id: Unique batch identifier
        filename: Name of completed file
        file_index: Index of file in batch (0-based)
        message: Completion message

    Example:
        send_batch_file_completed('batch-456', 'document5.pdf', 4, 'File 5 completed')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"batch_{batch_id}",
            {
                "type": "batch_file_completed",
                "filename": filename,
                "file_index": file_index,
                "message": message,
            },
        )
        logger.debug(f"Batch file completed: batch_id={batch_id}, file={filename}")
    except Exception as e:
        logger.error(f"Failed to send batch file completion: {e}")


def send_batch_completed(
    batch_id,
    download_url,
    total_files,
    successful_files,
    failed_files,
    message="Batch conversion completed",
):
    """
    Send batch completion notification via WebSocket.

    Args:
        batch_id: Unique batch identifier
        download_url: URL to download ZIP archive
        total_files: Total number of files
        successful_files: Number of successfully converted files
        failed_files: Number of failed files
        message: Completion message

    Example:
        send_batch_completed('batch-456', '/media/batch/result.zip', 10, 9, 1, 'Batch completed: 9/10 successful')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"batch_{batch_id}",
            {
                "type": "batch_completed",
                "download_url": download_url,
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "message": message,
            },
        )
        logger.info(
            f"Batch completed: batch_id={batch_id}, {successful_files}/{total_files} successful"
        )
    except Exception as e:
        logger.error(f"Failed to send batch completion: {e}")


def send_batch_error(batch_id, error_message, error_details=None):
    """
    Send batch error notification via WebSocket.

    Args:
        batch_id: Unique batch identifier
        error_message: User-friendly error message
        error_details: Technical error details (optional)

    Example:
        send_batch_error('batch-456', 'Batch conversion failed', 'Out of memory')
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"batch_{batch_id}",
            {
                "type": "batch_error",
                "message": error_message,
                "error": error_details or error_message,
            },
        )
        logger.error(f"Batch error sent: batch_id={batch_id}, error={error_message}")
    except Exception as e:
        logger.error(f"Failed to send batch error: {e}")


class ProgressTracker:
    """
    Context manager for tracking conversion progress with WebSocket updates.

    Usage:
        with ProgressTracker(task_id) as tracker:
            tracker.update(25, "Processing page 1...")
            # ... do work ...
            tracker.update(50, "Processing page 2...")
            # ... do work ...
            tracker.complete(download_url, filename)
    """

    def __init__(self, task_id):
        self.task_id = task_id
        self.current_progress = 0

    def __enter__(self):
        send_conversion_progress(
            self.task_id, 0, "Starting conversion...", "processing"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Error occurred
            error_msg = str(exc_val) if exc_val else "Conversion failed"
            send_conversion_error(self.task_id, error_msg, str(exc_type))
        return False  # Don't suppress exceptions

    def update(self, progress, message):
        """Update progress."""
        self.current_progress = progress
        send_conversion_progress(self.task_id, progress, message, "processing")

    def complete(self, download_url, filename, file_size=None):
        """Mark as completed."""
        send_conversion_completed(self.task_id, download_url, filename, file_size)

    def error(self, message, details=None):
        """Mark as error."""
        send_conversion_error(self.task_id, message, details)
