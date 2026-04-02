"""Batch image format conversion API views."""

import os

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import convert_image_docs
from .utils import convert_image


class ConvertImageBatchAPIView(BaseBatchAPIView):
    """Handle batch image format conversion requests."""

    CONVERSION_TYPE = "convert_image_batch"
    FILE_FIELD_NAME = "image_files"
    TMP_PREFIX = "convert_img_batch_"
    OUTPUT_ZIP_FILENAME = "convert_image_convertica.zip"

    def get_post_params(self, request):
        try:
            quality = int(request.POST.get("quality", 90))
            quality = max(10, min(100, quality))
        except (ValueError, TypeError):
            quality = 90
        return {
            "output_format": request.POST.get("output_format", "").upper(),
            "quality": quality,
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = convert_image(uploaded_file, **params)
        return os.path.dirname(output_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return os.path.basename(output_path)

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @convert_image_docs()
    def post(self, request: HttpRequest):
        # output_format is required for image conversion
        output_format = request.POST.get("output_format", "").upper()
        if not output_format:
            return Response(
                {
                    "error": "output_format is required (JPEG, PNG, WebP, GIF, BMP, TIFF)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._process_batch(request)
