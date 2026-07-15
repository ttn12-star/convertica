# views.py
import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpRequest
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from src.exceptions import ConversionError

from ...base_views import BaseConversionAPIView
from ...logging_utils import build_request_context, get_logger, log_conversion_error
from .decorators import password_protect_image_docs
from .serializers import PasswordProtectImageSerializer
from .utils import protect_image

logger = get_logger(__name__)


class PasswordProtectImageAPIView(BaseConversionAPIView):
    """Lock image(s) into one AES-256 password-protected PDF.

    One image → single path (full base validation via perform_conversion).
    Many images → overridden post (mirrors JPGToPDFAPIView multi branch).
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    CONVERSION_TYPE = "PASSWORD_PROTECT_IMAGE"
    FILE_FIELD_NAME = "image_files"
    # Multi-file branch renders synchronously in the request cycle; cap to keep
    # one request from hogging a gunicorn worker (matches JPGToPDFAPIView).
    MAX_MULTI_IMAGE_FILES = 50

    def get_serializer_class(self):
        return PasswordProtectImageSerializer

    def get_docs_decorator(self):
        return password_protect_image_docs

    def get(self, request: HttpRequest):
        return Response(
            {"error": "GET not allowed. Use POST to protect images."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @password_protect_image_docs()
    def post(self, request: HttpRequest):
        from asgiref.sync import async_to_sync

        uploaded_files: list[UploadedFile] = request.FILES.getlist(self.FILE_FIELD_NAME)
        if not uploaded_files:
            return Response(
                {"error": f"{self.FILE_FIELD_NAME} is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(uploaded_files) == 1:
            return async_to_sync(self.post_async)(request)
        if len(uploaded_files) > self.MAX_MULTI_IMAGE_FILES:
            return Response(
                {
                    "error": _(
                        "Too many files. Maximum is %(max_files)d images per request."
                    )
                    % {"max_files": self.MAX_MULTI_IMAGE_FILES}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password", "")
        if not password or not password.strip():
            return Response(
                {"error": _("Password is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for uf in uploaded_files:
            err = self.validate_file_basic(
                uf, build_request_context(request, uploaded_file=uf)
            )
            if err:
                return err

        try:
            quality = int(request.data.get("quality", 85))
        except (TypeError, ValueError):
            quality = 85

        try:
            _in, output_path = protect_image(
                uploaded_files,
                password=password,
                user_password=request.data.get("user_password"),
                owner_password=request.data.get("owner_password"),
                quality=quality,
            )
        except ConversionError as e:
            # protect_image creates its own temp dir internally and doesn't
            # expose the path on failure, so it can't be rmtree'd here; the
            # periodic tmp-dir sweep reclaims it. What we CAN and must do is
            # turn this into a clean 4xx instead of an unhandled 500 (this
            # overridden post() bypasses BaseConversionAPIView's post()/
            # handle_conversion_error, which never runs for this branch).
            log_conversion_error(
                logger,
                self.CONVERSION_TYPE,
                build_request_context(request),
                e,
                level="warning",
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        tmp_dir = os.path.dirname(output_path)
        try:
            # fd lifetime owned by FileResponse; rmtree only unlinks the path.
            fh = open(output_path, "rb")  # noqa: SIM115
            return FileResponse(
                fh,
                content_type="application/pdf",
                as_attachment=True,
                filename="protected_convertica.pdf",
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Single-image path. Returns (input_path, output_path)."""
        try:
            quality = int(kwargs.get("quality", 85))
        except (TypeError, ValueError):
            quality = 85
        input_path, output_path = protect_image(
            [uploaded_file],
            password=kwargs.get("password", ""),
            user_password=kwargs.get("user_password"),
            owner_password=kwargs.get("owner_password"),
            quality=quality,
        )
        return input_path, output_path
