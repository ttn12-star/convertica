# views.py

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response

from ...base_views import BaseConversionAPIView
from ...premium_utils import is_premium_active
from .decorators import protect_pdf_docs
from .serializers import ProtectPDFSerializer
from .utils import protect_pdf

_RESTRICT_FIELDS = ("restrict_printing", "restrict_copying", "restrict_modifying")


class ProtectPDFAPIView(BaseConversionAPIView):
    """Handle protect PDF requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}
    CONVERSION_TYPE = "PROTECT_PDF"
    FILE_FIELD_NAME = "pdf_file"

    def get_serializer_class(self):
        return ProtectPDFSerializer

    def get_docs_decorator(self):
        return protect_pdf_docs

    @protect_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation."""
        # Permission toggles are premium-only (client disables the boxes,
        # but a forged form field must not restrict for free either).
        wants_restrictions = any(
            str(request.data.get(field, "")).lower() in ("true", "1", "on")
            for field in _RESTRICT_FIELDS
        )
        if wants_restrictions:
            user = getattr(request, "user", None)
            premium = bool(
                user
                and getattr(user, "is_authenticated", False)
                and is_premium_active(user)
            )
            if not premium or not getattr(settings, "PAYMENTS_ENABLED", True):
                return Response(
                    {
                        "error": _(
                            "Permission controls (restrict printing, copying "
                            "or editing) are a Premium feature. Untick them "
                            "to protect with a password only, or upgrade "
                            "to Premium."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        return super().post(request)

    def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Protect PDF with password."""
        password = kwargs.get("password", "")
        user_password = kwargs.get("user_password")
        owner_password = kwargs.get("owner_password")
        pdf_path, output_path = protect_pdf(
            uploaded_file,
            password=password,
            user_password=user_password,
            owner_password=owner_password,
            suffix="_convertica",
            restrict_printing=bool(kwargs.get("restrict_printing")),
            restrict_copying=bool(kwargs.get("restrict_copying")),
            restrict_modifying=bool(kwargs.get("restrict_modifying")),
        )
        return pdf_path, output_path
