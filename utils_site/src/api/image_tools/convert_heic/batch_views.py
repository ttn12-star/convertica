"""Batch HEIC / HEIF converter API view (premium-gated)."""

import os

from django.conf import settings
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from ...base_batch_views import BaseBatchAPIView
from ...premium_utils import is_premium_active
from ...rate_limit_utils import combined_rate_limit
from .decorators import convert_heic_docs
from .utils import convert_heic


def _premium_access_error(request: HttpRequest) -> Response:
    payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
    if not request.user.is_authenticated:
        if payments_enabled:
            message = (
                "This converter is available for premium users. "
                "Please log in and upgrade."
            )
        else:
            message = "This converter is currently unavailable."
    else:
        if payments_enabled:
            message = (
                "This converter is available for premium users. "
                "Upgrade to Premium to continue."
            )
        else:
            message = "This converter is currently unavailable."
    return Response({"error": message}, status=status.HTTP_403_FORBIDDEN)


class ConvertHEICBatchAPIView(BaseBatchAPIView):
    """Batch HEIC → JPG/PNG/PDF for premium users."""

    CONVERSION_TYPE = "convert_heic_batch"
    FILE_FIELD_NAME = "image_files"
    TMP_PREFIX = "convert_heic_batch_"
    OUTPUT_ZIP_FILENAME = "convert_heic_convertica.zip"

    def get_post_params(self, request):
        try:
            quality = int(request.POST.get("quality", 90))
            quality = max(10, min(100, quality))
        except (ValueError, TypeError):
            quality = 90
        return {
            "output_format": request.POST.get("output_format", "JPEG").upper(),
            "quality": quality,
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = convert_heic(uploaded_file, **params)
        return os.path.dirname(output_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return os.path.basename(output_path)

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @convert_heic_docs()
    def post(self, request: HttpRequest):
        if not is_premium_active(request.user):
            return _premium_access_error(request)
        output_format = request.POST.get("output_format", "JPEG").upper()
        if output_format not in {"JPEG", "JPG", "PNG", "PDF"}:
            return Response(
                {"error": "output_format must be one of JPEG, JPG, PNG, or PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._process_batch(request)
