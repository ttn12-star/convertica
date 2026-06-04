"""Feedback API: POST a 1-5 star rating (+ comment) for a finished operation."""

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from src.users.models import OperationRun

from .models import ToolRating
from .serializers import FeedbackSerializer
from .tokens import resolve_feedback_token


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def _ok():
    # Generic OK that never reveals whether the token was valid (anti-probing).
    return Response({"detail": "ok"}, status=status.HTTP_200_OK)


class FeedbackAPIView(APIView):
    """Anonymous-friendly. The signed feedback_token is the abuse gate."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        resolved = resolve_feedback_token(data["feedback_token"])
        if not resolved:
            return _ok()

        kind, value = resolved
        if kind == "r":
            qs = OperationRun.objects.filter(request_id=value)
        else:
            qs = OperationRun.objects.filter(task_id=value)
        op = qs.order_by("-created_at").first()
        if op is None or op.status != "success":
            return _ok()

        try:
            # atomic() so a duplicate (unique constraint) rolls back only this
            # savepoint instead of poisoning the surrounding transaction.
            with transaction.atomic():
                ToolRating.objects.create(
                    tool_slug=op.conversion_type,
                    rating=data["rating"],
                    comment=(data.get("comment") or "").strip(),
                    operation_run=op,
                    user=request.user if request.user.is_authenticated else None,
                    session_key=getattr(request.session, "session_key", "") or "",
                    lang=getattr(request, "LANGUAGE_CODE", "") or "",
                    ip_address=_client_ip(request),
                )
        except IntegrityError:
            # Operation already rated — idempotent success.
            return _ok()

        return Response({"detail": "thanks"}, status=status.HTTP_201_CREATED)
