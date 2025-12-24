"""
Push notification utilities for PWA.
Sends push notifications to users when conversions complete.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def send_push_notification(
    subscription: dict[str, Any],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    icon: str = "/static/favicon-192x192.png",
    badge: str = "/static/favicon-96x96.png",
    tag: str = "convertica-notification",
    require_interaction: bool = False,
) -> bool:
    """
    Send push notification to user's device via Web Push API.

    Args:
        subscription: User's push subscription object (from browser)
        title: Notification title
        body: Notification body text
        data: Additional data to send with notification
        icon: Notification icon URL
        badge: Notification badge URL
        tag: Notification tag (for grouping)
        require_interaction: Whether notification requires user interaction

    Returns:
        True if notification sent successfully, False otherwise

    Example:
        subscription = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/...',
            'keys': {
                'p256dh': '...',
                'auth': '...'
            }
        }

        send_push_notification(
            subscription,
            title='Conversion Complete!',
            body='Your PDF is ready to download',
            data={'url': '/download/file.pdf'}
        )
    """
    try:
        # Import pywebpush library
        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            logger.error("pywebpush library not installed. Run: pip install pywebpush")
            return False

        # Prepare notification payload
        payload = {
            "title": title,
            "body": body,
            "icon": icon,
            "badge": badge,
            "tag": tag,
            "requireInteraction": require_interaction,
            "data": data or {},
            "actions": [
                {"action": "open", "title": "Open"},
                {"action": "close", "title": "Close"},
            ],
        }

        # Get VAPID keys from settings
        from django.conf import settings

        vapid_private_key = getattr(settings, "VAPID_PRIVATE_KEY", None)
        vapid_claims = getattr(
            settings, "VAPID_CLAIMS", {"sub": "mailto:admin@convertica.net"}
        )

        if not vapid_private_key:
            logger.warning("VAPID_PRIVATE_KEY not configured in settings")
            return False

        # Send push notification
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims,
        )

        logger.info(f"Push notification sent: {title}")
        return True

    except WebPushException as e:
        logger.error(f"WebPush error: {e}")

        # Handle subscription expiration
        if e.response and e.response.status_code in [404, 410]:
            logger.info("Push subscription expired, marking as inactive")
            # Mark subscription as inactive (will be cleaned up by maintenance task)
            try:
                if hasattr(subscription, "is_active"):
                    subscription.is_active = False
                    subscription.save()
            except Exception:
                pass

        return False

    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False


def send_conversion_complete_notification(
    user, filename: str, download_url: str, file_size: int | None = None
) -> bool:
    """
    Send conversion complete notification to user.

    Args:
        user: Django user object
        filename: Name of converted file
        download_url: URL to download the file
        file_size: Size of file in bytes (optional)

    Returns:
        True if notification sent successfully

    Example:
        send_conversion_complete_notification(
            user=request.user,
            filename='document.docx',
            download_url='/media/converted/document.docx',
            file_size=245760
        )
    """
    # Check if user has push subscription
    if not hasattr(user, "push_subscription") or not user.push_subscription:
        logger.debug(f"User {user.id} has no push subscription")
        return False

    # Format file size
    size_str = ""
    if file_size:
        if file_size < 1024:
            size_str = f" ({file_size} B)"
        elif file_size < 1024 * 1024:
            size_str = f" ({file_size / 1024:.1f} KB)"
        else:
            size_str = f" ({file_size / (1024 * 1024):.1f} MB)"

    # Send notification
    return send_push_notification(
        subscription=user.push_subscription,
        title="Conversion Complete! 🎉",
        body=f"{filename}{size_str} is ready to download",
        data={
            "url": download_url,
            "filename": filename,
            "file_size": file_size,
            "type": "conversion_complete",
        },
        tag="conversion-complete",
    )


def send_batch_complete_notification(
    user, total_files: int, successful_files: int, download_url: str
) -> bool:
    """
    Send batch conversion complete notification.

    Args:
        user: Django user object
        total_files: Total number of files in batch
        successful_files: Number of successfully converted files
        download_url: URL to download ZIP archive

    Returns:
        True if notification sent successfully

    Example:
        send_batch_complete_notification(
            user=request.user,
            total_files=10,
            successful_files=9,
            download_url='/media/batch/result.zip'
        )
    """
    if not hasattr(user, "push_subscription") or not user.push_subscription:
        return False

    # Create message based on success rate
    if successful_files == total_files:
        body = f"All {total_files} files converted successfully!"
    else:
        body = f"{successful_files} of {total_files} files converted successfully"

    return send_push_notification(
        subscription=user.push_subscription,
        title="Batch Conversion Complete! 🎉",
        body=body,
        data={
            "url": download_url,
            "total_files": total_files,
            "successful_files": successful_files,
            "type": "batch_complete",
        },
        tag="batch-complete",
    )


# Example usage in Celery task
"""
from src.api.push_notifications import send_conversion_complete_notification
from src.api.websocket_utils import send_conversion_completed

@shared_task
def convert_pdf_to_word_task(task_id, pdf_path, user_id):
    try:
        # Perform conversion
        docx_path = convert_pdf_to_docx(pdf_path)
        download_url = get_download_url(docx_path)
        filename = os.path.basename(docx_path)
        file_size = os.path.getsize(docx_path)

        # Send WebSocket notification (real-time)
        send_conversion_completed(task_id, download_url, filename, file_size)

        # Send Push notification (works even if app closed)
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                send_conversion_complete_notification(
                    user=user,
                    filename=filename,
                    download_url=download_url,
                    file_size=file_size
                )
            except User.DoesNotExist:
                pass

        return {'status': 'success', 'download_url': download_url}

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return {'status': 'error', 'message': str(e)}
"""
