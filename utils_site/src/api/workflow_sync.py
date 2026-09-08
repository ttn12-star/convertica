"""Premium: server-side sync of Saved Workflows presets.

GET returns the stored preset list and Workbench boards; PUT replaces presets
wholesale and, when "boards" is present, boards too (the client treats
localStorage as a cache and pushes the full set after every change).
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
MAX_BOARDS = 5
MAX_TILES = 20
_STR_FIELDS = {
    "id": 40,
    "name": 80,
    "toolUrl": 200,
    "toolLabel": 80,
    "notes": 240,
    "toolKey": 60,
}
MAX_PARAM_KEYS = 30
MAX_PARAM_VALUE_LEN = 200
TILE_KINDS = {"preset", "activity", "tasks", "quota"}
TILE_SIZES = {"s", "m", "l"}


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
    from src.frontend.tool_configs import TOOL_CONFIGS

    if preset["toolKey"] not in TOOL_CONFIGS:
        preset["toolKey"] = ""
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


def _clean_tile(raw, preset_ids: set[str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    if kind not in TILE_KINDS:
        return None
    tile = {
        "id": str(raw.get("id") or "")[:40],
        "kind": kind,
        "size": raw.get("size") if raw.get("size") in TILE_SIZES else "m",
    }
    if not tile["id"]:
        return None
    if kind == "preset":
        preset_id = str(raw.get("presetId") or "")[:40]
        if preset_id not in preset_ids:
            return None
        tile["presetId"] = preset_id
    return tile


def _clean_board(raw, preset_ids: set[str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    board_id = str(raw.get("id") or "")[:40]
    name = raw.get("name")
    if not board_id or not isinstance(name, str) or not name.strip():
        return None
    tiles_raw = raw.get("tiles")
    tiles = (
        [t for t in (_clean_tile(x, preset_ids) for x in tiles_raw[:MAX_TILES]) if t]
        if isinstance(tiles_raw, list)
        else []
    )
    board = {
        "id": board_id,
        "name": name.strip()[:60],
        "isDefault": bool(raw.get("isDefault")),
        "tiles": tiles,
    }
    created_at = raw.get("createdAt")
    if isinstance(created_at, int | float):
        board["createdAt"] = int(created_at)
    return board


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
        return Response(
            {"presets": row.presets if row else [], "boards": row.boards if row else []}
        )

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

        raw_boards = request.data.get("boards", None)
        if raw_boards is None:
            row = UserWorkflowSet.objects.filter(user=request.user).first()
            boards = row.boards if row else []
        else:
            if not isinstance(raw_boards, list):
                return Response(
                    {"error": _("boards must be a list.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(raw_boards) > MAX_BOARDS:
                return Response(
                    {"error": _("Up to 5 boards are supported.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            preset_ids = {p["id"] for p in cleaned}
            boards = [b for b in (_clean_board(x, preset_ids) for x in raw_boards) if b]

        UserWorkflowSet.objects.update_or_create(
            user=request.user, defaults={"presets": cleaned, "boards": boards}
        )
        return Response({"presets": cleaned, "boards": boards})
