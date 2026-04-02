"""Batch image optimisation API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import optimize_image_docs
from .utils import optimize_image


class OptimizeImageBatchAPIView(BaseBatchAPIView):
    """Handle batch image optimisation requests."""

    CONVERSION_TYPE = "optimize_image_batch"
    FILE_FIELD_NAME = "image_files"
    TMP_PREFIX = "optimize_img_batch_"
    OUTPUT_ZIP_FILENAME = "optimize_image_convertica.zip"

    def get_post_params(self, request):
        try:
            quality = int(request.POST.get("quality", 85))
            quality = max(10, min(100, quality))
        except (ValueError, TypeError):
            quality = 85
        try:
            max_width = (
                int(request.POST.get("max_width"))
                if request.POST.get("max_width")
                else None
            )
        except (ValueError, TypeError):
            max_width = None
        try:
            max_height = (
                int(request.POST.get("max_height"))
                if request.POST.get("max_height")
                else None
            )
        except (ValueError, TypeError):
            max_height = None
        return {
            "quality": quality,
            "output_format": request.POST.get("output_format", "") or None,
            "max_width": max_width,
            "max_height": max_height,
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = optimize_image(uploaded_file, **params)
        return os.path.dirname(output_path), output_path

    # Use the output filename directly (may have a different extension after format change)
    def get_zip_entry_name(self, original_name, output_path):
        return os.path.basename(output_path)

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @optimize_image_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
