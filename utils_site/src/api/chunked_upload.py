"""Chunked uploads: files bigger than one request body Cloudflare accepts.

Cloudflare (Free/Pro) answers a request body over 100 MB with a 413 before it
reaches us, while premium allows 200 MB files. The browser uploads such a file
in 50 MB chunks to ``/api/uploads/chunk/`` (static/js/utils.js,
_installChunkedUpload); the conversion request then carries
``<field>__upload_id`` instead of the file, and ChunkedUploadMiddleware puts the
assembled file back into ``request.FILES``. Every tool works unchanged and the
usual per-tier size checks still see the real file.

Uploads live in ASYNC_TEMP_DIR/upload_<id>/: deleted after the request that
consumes them, and by the async_temp reaper (1 h) if it never comes.
"""

import fcntl
import glob
import json
import os
import re
import shutil
import uuid

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .async_views import ASYNC_TEMP_DIR
from .file_validation import check_disk_space, sanitize_filename
from .logging_utils import get_logger
from .premium_utils import is_premium_active

logger = get_logger(__name__)

UPLOAD_ID_SUFFIX = "__upload_id"
# The browser sends 50 MB; anything near Cloudflare's 100 MB would never get here.
CHUNK_MAX_BYTES = 60 * 1024 * 1024
_UPLOAD_ID = re.compile(r"[0-9a-f]{32}")
MAX_UPLOADS_PER_USER = 3


def _upload_dir(upload_id: str) -> str:
    return os.path.join(ASYNC_TEMP_DIR, f"upload_{upload_id}")


def _load_meta(upload_id: str) -> dict | None:
    if not _UPLOAD_ID.fullmatch(upload_id or ""):
        return None
    try:
        with open(os.path.join(_upload_dir(upload_id), "meta.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _start_upload(user, total: int, request) -> tuple[str | None, dict | None, str]:
    """Open a new upload; returns (upload_id, meta, error)."""
    has_space, _reason = check_disk_space(
        ASYNC_TEMP_DIR, required_mb=total // (1024 * 1024) + 500
    )
    if not has_space:
        return None, None, _("The server is out of space; please try again later.")
    # Bound the disk one account can hold: keep its newest uploads only. A
    # normal user has one in flight; leftovers from failed attempts go first.
    mine = []
    for folder in glob.glob(os.path.join(ASYNC_TEMP_DIR, "upload_*")):
        meta = _load_meta(os.path.basename(folder)[len("upload_") :])
        if meta and meta["user_id"] == user.pk:
            mine.append((os.path.getmtime(folder), folder))
    for _mtime, folder in sorted(mine)[
        : max(0, len(mine) - (MAX_UPLOADS_PER_USER - 1))
    ]:
        shutil.rmtree(folder, ignore_errors=True)

    upload_id = uuid.uuid4().hex
    os.makedirs(_upload_dir(upload_id))
    meta = {
        "user_id": user.pk,
        "filename": sanitize_filename(request.POST.get("filename") or "upload"),
        "content_type": request.POST.get("content_type") or "",
        "total": total,
        "received": 0,
        "next_index": 0,
    }
    return upload_id, meta, ""


@require_POST
def chunk_upload(request):
    """Write one chunk; the first chunk (index 0, no upload_id) opens an upload."""
    user = request.user
    if not is_premium_active(user):
        # Free files are capped far below one request body; nobody else needs this.
        return _error(_("This file is larger than your plan allows."), 403)

    chunk = request.FILES.get("chunk")
    try:
        index = int(request.POST.get("index", ""))
        total = int(request.POST.get("total_size", ""))
    except ValueError:
        return _error(_("Invalid upload request."), 400)
    limit = getattr(settings, "MAX_FILE_SIZE_PREMIUM", 200 * 1024 * 1024)
    if chunk is None or chunk.size > CHUNK_MAX_BYTES or not 0 < total <= limit:
        return _error(_("This file is larger than your plan allows."), 400)

    upload_id = request.POST.get("upload_id") or ""
    if index == 0 and not upload_id:
        if chunk.size > total:
            return _error(_("Invalid upload request."), 400)
        upload_id, meta, problem = _start_upload(user, total, request)
        if problem:
            return _error(problem, 507)
    elif _load_meta(upload_id) is None:
        return _error(_("The upload expired; please upload the file again."), 404)

    folder = _upload_dir(upload_id)
    # One writer per upload: parallel requests for the same index used to
    # each append, leaving more bytes on disk than the size checks were told.
    with open(os.path.join(folder, "lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if index != 0 or request.POST.get("upload_id"):
            meta = _load_meta(upload_id)
            if meta is None or meta["user_id"] != user.pk:
                return _error(
                    _("The upload expired; please upload the file again."), 404
                )
            if index != meta["next_index"] or total != meta["total"]:
                return _error(
                    _("Upload interrupted; please upload the file again."), 409
                )
            if meta["received"] + chunk.size > meta["total"]:
                return _error(_("Invalid upload request."), 400)

        data_path = os.path.join(folder, "data")
        with open(data_path, "r+b" if os.path.exists(data_path) else "wb") as out:
            out.seek(meta["received"])  # a repeated index overwrites, never grows
            for piece in chunk.chunks():
                out.write(piece)
            out.truncate()
        meta["received"] += chunk.size
        meta["next_index"] = index + 1
        with open(os.path.join(folder, "meta.json"), "w") as f:
            json.dump(meta, f)
        os.utime(folder)  # the async_temp reaper ages folders by mtime

    return JsonResponse(
        {
            "upload_id": upload_id,
            "received": meta["received"],
            "complete": meta["received"] == meta["total"],
        }
    )


class ChunkedUploadMiddleware:
    """Swap ``<field>__upload_id`` form values for the assembled files.

    Runs after authentication (uploads belong to a user) and before anything
    that inspects request.FILES (analytics, quota). DRF reuses request.POST and
    request.FILES once a middleware has parsed them, so views see plain files.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not (
            request.method == "POST"
            and request.path.startswith("/api/")
            and not request.path.startswith("/api/uploads/")
            and request.content_type == "multipart/form-data"
        ):
            return self.get_response(request)

        used, opened = [], []
        try:
            for key in list(request.POST.keys()):
                if not key.endswith(UPLOAD_ID_SUFFIX):
                    continue
                field = key[: -len(UPLOAD_ID_SUFFIX)]
                for upload_id in request.POST.getlist(key):
                    meta = _load_meta(upload_id)
                    path = os.path.join(_upload_dir(upload_id or "x"), "data")
                    if (
                        meta is None
                        or meta["user_id"] != getattr(request.user, "pk", None)
                        or meta["received"] != meta["total"]
                        or not os.path.exists(path)
                        or os.path.getsize(path) != meta["total"]
                    ):
                        return _error(
                            _("The upload expired; please upload the file again."), 400
                        )
                    used.append(upload_id)
                    uploaded = UploadedFile(
                        file=open(path, "rb"),  # noqa: SIM115 - closed in finally
                        name=meta["filename"],
                        content_type=meta["content_type"],
                        size=meta["total"],
                    )
                    opened.append(uploaded)
                    request.FILES.appendlist(field, uploaded)
            return self.get_response(request)
        finally:
            for uploaded in opened:
                try:
                    uploaded.close()
                except Exception:
                    pass
            for upload_id in used:
                # Single use: a sync tool is done with it, an async one copied
                # it into its task dir during the request.
                shutil.rmtree(_upload_dir(upload_id), ignore_errors=True)
