"""Premium: server-side sync of Saved Workflows presets.

GET returns the stored preset list; PUT replaces it wholesale (the client
treats localStorage as a cache and pushes the full set after every change).
Last write wins — presets are personal shortcuts, not collaborative data.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .logging_utils import get_logger
from .premium_utils import is_premium_active

logger = get_logger(__name__)

MAX_PRESETS = 40
_STR_FIELDS = {"id": 40, "name": 80, "toolUrl": 200, "toolLabel": 80, "notes": 240}
MAX_PARAM_KEYS = 30
MAX_PARAM_VALUE_LEN = 200


def _clean_preset(raw) -> dict | None:
    """Whitelist-validate one preset; None if it is not salvageable."""
    if not isinstance(raw, dict):
        return None
    preset = {}
    for field, max_len in _STR_FIELDS.items():
        value = raw.get(field, "")
        if not isinstance(value, str):
            value = str(value) if value is not None else ""
        preset[field] = value[:max_len]
    if not preset["name"] or not preset["toolUrl"].startswith("/"):
        return None
    params = raw.get("params")
    if isinstance(params, dict):
        clean_params = {}
        for key, value in list(params.items())[:MAX_PARAM_KEYS]:
            if not isinstance(key, str):
                continue
            if isinstance(value, bool):
                clean_params[key[:80]] = value
            elif isinstance(value, str | int | float):
                clean_params[key[:80]] = str(value)[:MAX_PARAM_VALUE_LEN]
        if clean_params:
            preset["params"] = clean_params
    created_at = raw.get("createdAt")
    if isinstance(created_at, int | float):
        preset["createdAt"] = int(created_at)
    return preset


class WorkflowSyncAPIView(APIView):
    """GET/PUT the authenticated premium user's preset set."""

    def _gate(self, request):
        user = getattr(request, "user", None)
        if not (user and getattr(user, "is_authenticated", False)):
            return Response(
                {"error": _("Sign in to sync workflows.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not is_premium_active(user):
            return Response(
                {"error": _("Workflow sync is a Premium feature.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def get(self, request):
        denied = self._gate(request)
        if denied:
            return denied
        from src.users.models import UserWorkflowSet

        row = UserWorkflowSet.objects.filter(user=request.user).first()
        return Response({"presets": row.presets if row else []})

    def put(self, request):
        denied = self._gate(request)
        if denied:
            return denied
        raw = request.data.get("presets")
        if not isinstance(raw, list):
            return Response(
                {"error": _("presets must be a list.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(raw) > MAX_PRESETS:
            return Response(
                {"error": _("Up to 40 presets are supported.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cleaned = [p for p in (_clean_preset(item) for item in raw) if p]

        from src.users.models import UserWorkflowSet

        UserWorkflowSet.objects.update_or_create(
            user=request.user, defaults={"presets": cleaned}
        )
        return Response({"presets": cleaned})
