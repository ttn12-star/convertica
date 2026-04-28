import functools
import json
import logging
import time
import uuid

from django.utils import timezone

logger = logging.getLogger("src.api.operation_run_tracking")


def _safe_is_premium(request) -> bool:
    try:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if not getattr(user, "is_premium", False):
            return False
        is_active = getattr(user, "is_subscription_active", None)
        if callable(is_active):
            return bool(is_active())
        return bool(is_active)
    except Exception:
        return False


def _get_remote_addr(request) -> str:
    try:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
    except Exception:
        return ""


def extract_error_message(response) -> str:
    return _extract_error_message(response)


def _format_with_details(error_part: str, data: dict) -> str:
    """Append `details` to error_part when present, so validation failures keep field info."""
    details = data.get("details")
    if not details:
        return error_part
    try:
        details_str = json.dumps(details, ensure_ascii=False)[:1500]
    except Exception:
        details_str = str(details)[:1500]
    return f"{error_part}: {details_str}" if error_part else details_str


def _extract_from_dict(data: dict) -> str:
    for key in ("error", "message", "detail"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return _format_with_details(val.strip(), data)
    return json.dumps(data)[:2000]


def _extract_error_message(response) -> str:
    try:
        data = getattr(response, "data", None)
        if isinstance(data, dict):
            return _extract_from_dict(data)
    except Exception:
        pass

    try:
        content = getattr(response, "content", b"")
        if not content:
            return ""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        content = str(content)
        if not content.strip():
            return ""
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                return _extract_from_dict(obj)
        except Exception:
            pass
        return content.strip()[:2000]
    except Exception:
        return ""


def ensure_request_id(request) -> str:
    request_id = getattr(request, "id", None)
    if request_id:
        return str(request_id)
    request_id = uuid.uuid4().hex
    request.id = request_id
    return request_id


def create_operation_run(
    *,
    request,
    conversion_type: str,
    status: str,
    started_at=None,
    **extra_fields,
) -> str | None:
    try:
        from src.users.models import OperationRun

        request_id = ensure_request_id(request)
        now = timezone.now()

        if started_at is None:
            started_at = now

        defaults = {
            "conversion_type": str(conversion_type or "")[:80],
            "status": status,
            "user": (
                request.user
                if getattr(request, "user", None) and request.user.is_authenticated
                else None
            ),
            "is_premium": _safe_is_premium(request),
            "started_at": started_at,
            "remote_addr": _get_remote_addr(request),
            "user_agent": str(request.META.get("HTTP_USER_AGENT", "") or ""),
            "path": str(getattr(request, "path", "") or ""),
            **extra_fields,
        }

        OperationRun.objects.update_or_create(
            request_id=str(request_id),
            defaults=defaults,
        )
        return request_id
    except Exception as e:
        logger.warning("OperationRun create failed: %s: %s", type(e).__name__, e)
        return None


def upsert_operation_run(*, request_id: str, defaults: dict) -> None:
    try:
        from src.users.models import OperationRun

        if not request_id:
            return

        OperationRun.objects.update_or_create(
            request_id=str(request_id),
            defaults=defaults,
        )
    except Exception as e:
        logger.warning("OperationRun upsert failed: %s: %s", type(e).__name__, e)


def update_operation_run(*, request_id: str, **fields) -> None:
    try:
        from src.users.models import OperationRun

        if not request_id:
            return
        OperationRun.objects.filter(request_id=str(request_id)).update(**fields)
    except Exception as e:
        logger.warning("OperationRun update failed: %s: %s", type(e).__name__, e)


def mark_success(*, request_id: str, output_size: int | None, duration_ms: int) -> None:
    fields = {
        "status": "success",
        "finished_at": timezone.now(),
        "duration_ms": duration_ms,
    }
    if output_size is not None:
        fields["output_size"] = output_size
    update_operation_run(request_id=request_id, **fields)


def mark_error(
    *, request_id: str, error_type: str, error_message: str, duration_ms: int
) -> None:
    update_operation_run(
        request_id=request_id,
        status="error",
        finished_at=timezone.now(),
        duration_ms=duration_ms,
        error_type=str(error_type or "")[:120],
        error_message=str(error_message or "")[:2000],
    )


def mark_http_error(
    *,
    request_id: str,
    error_message: str,
    duration_ms: int,
    status_code: int | None = None,
) -> None:
    """Mark operation as failed for an HTTP error response.

    4xx → status="rejected" (user-input issue: validation, unsupported file, premium gate).
    5xx (or unknown) → status="error" (server-side failure).
    """
    try:
        from django.db.models import Case, CharField, F, TextField, Value, When
        from src.users.models import OperationRun

        if not request_id:
            return

        msg = str(error_message or "")[:2000]

        is_client_error = status_code is not None and 400 <= int(status_code) < 500
        new_status = "rejected" if is_client_error else "error"
        default_error_type = "ClientError" if is_client_error else "HttpError"

        OperationRun.objects.filter(request_id=str(request_id)).update(
            status=new_status,
            finished_at=timezone.now(),
            duration_ms=duration_ms,
            error_type=Case(
                When(error_type="", then=Value(default_error_type)),
                default=F("error_type"),
                output_field=CharField(),
            ),
            error_message=Case(
                When(error_message="", then=Value(msg)),
                default=F("error_message"),
                output_field=TextField(),
            ),
        )
    except Exception as e:
        logger.warning(
            "OperationRun mark_http_error failed: %s: %s", type(e).__name__, e
        )


def track_operation_run(conversion_type: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            op_started_ts = time.time()
            request_id = create_operation_run(
                request=request,
                conversion_type=conversion_type,
                status="running",
            )

            try:
                response = func(self, request, *args, **kwargs)
            except Exception as exc:
                if request_id:
                    duration_ms = int((time.time() - op_started_ts) * 1000)
                    mark_error(
                        request_id=request_id,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:2000],
                        duration_ms=duration_ms,
                    )
                raise

            if request_id:
                duration_ms = int((time.time() - op_started_ts) * 1000)
                status_code = getattr(response, "status_code", 200)
                if status_code and int(status_code) >= 400:
                    msg = extract_error_message(response) or f"HTTP {status_code}"
                    mark_http_error(
                        request_id=request_id,
                        error_message=msg,
                        duration_ms=duration_ms,
                        status_code=int(status_code),
                    )
                else:
                    mark_success(
                        request_id=request_id,
                        output_size=None,
                        duration_ms=duration_ms,
                    )

            return response

        return wrapper

    return decorator
