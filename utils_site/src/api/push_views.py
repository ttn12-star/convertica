"""Premium: web-push subscription management.

POST stores the browser's push subscription (endpoint + keys) for the
authenticated premium user; DELETE removes it (user switched the toggle
off or revoked permission). The actual sending lives in src/tasks/push.py.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .logging_utils import get_logger
from .premium_utils import is_premium_active

logger = get_logger(__name__)


class PushSubscribeAPIView(APIView):
    """POST/DELETE the caller's web-push subscription."""

    def _gate(self, request):
        user = getattr(request, "user", None)
        if not (user and getattr(user, "is_authenticated", False)):
            return Response(
                {"error": _("Sign in to manage notifications.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not is_premium_active(user):
            return Response(
                {"error": _("Push notifications are a Premium feature.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @staticmethod
    def _extract(request):
        endpoint = request.data.get("endpoint", "")
        keys = request.data.get("keys") or {}
        p256dh = keys.get("p256dh", "") if isinstance(keys, dict) else ""
        auth = keys.get("auth", "") if isinstance(keys, dict) else ""
        if (
            not isinstance(endpoint, str)
            or not endpoint.startswith("https://")
            or len(endpoint) > 1000
        ):
            return None
        return endpoint, str(p256dh)[:255], str(auth)[:255]

    def post(self, request):
        denied = self._gate(request)
        if denied:
            return denied
        extracted = self._extract(request)
        if not extracted or not extracted[1] or not extracted[2]:
            return Response(
                {"error": _("Invalid subscription payload.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        endpoint, p256dh, auth = extracted

        from src.users.models import PushSubscription

        # endpoint is globally unique — a re-subscribe in another account's
        # browser session simply reassigns the row.
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
        )
        return Response({"subscribed": True})

    def delete(self, request):
        denied = self._gate(request)
        if denied:
            return denied
        endpoint = request.data.get("endpoint", "")

        from src.users.models import PushSubscription

        deleted, _count = PushSubscription.objects.filter(
            user=request.user, endpoint=endpoint
        ).delete()
        return Response({"subscribed": False, "removed": bool(deleted)})
