"""Web-push delivery for finished background conversions.

Enqueued by the conversion tasks (webhook/email pattern). Sends to every
subscription of the user; endpoints the push service reports gone (404/410)
are pruned so the table never accumulates dead browsers.
"""

import json

from celery import shared_task
from src.api.logging_utils import get_logger

logger = get_logger(__name__)


@shared_task(
    name="push.send_conversion_ready",
    queue="default",
    bind=True,
    max_retries=2,
    soft_time_limit=30,
    time_limit=60,
)
def send_conversion_ready(
    self, user_id: int, task_id: str, output_filename: str, lang: str = ""
):
    """Push a "your file is ready" notification to all the user's browsers."""
    from django.conf import settings
    from django.utils import translation
    from pywebpush import WebPushException, webpush
    from src.users.models import PushSubscription

    private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not private_key:
        logger.info("send_conversion_ready: VAPID keys unset, skipping")
        return

    subscriptions = list(PushSubscription.objects.filter(user_id=user_id))
    if not subscriptions:
        return

    supported = {code for code, _label in settings.LANGUAGES}
    lang = lang if lang in supported else settings.LANGUAGE_CODE
    with translation.override(lang):
        from django.utils.translation import gettext as _

        payload = json.dumps(
            {
                "title": _("Your file is ready"),
                "body": output_filename,
                "tag": f"conversion-{task_id}",
                "data": {"url": f"/{lang}/premium/background-center/"},
            }
        )

    sent = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.as_subscription_info(),
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(getattr(settings, "VAPID_CLAIMS", {})),
                ttl=3600,  # matches the 1h life of the result file
            )
            sent += 1
        except WebPushException as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code in (404, 410):
                subscription.delete()
                logger.info(
                    "Pruned dead push subscription",
                    extra={"event": "push_pruned", "user_id": user_id},
                )
            else:
                logger.warning("webpush failed, ignoring: %s", exc)

    logger.info(
        "Conversion push sent",
        extra={
            "event": "push_sent",
            "task_id": task_id,
            "user_id": user_id,
            "sent": sent,
        },
    )
