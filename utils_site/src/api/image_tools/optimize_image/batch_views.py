"""
Batch image optimization API views.

Supports processing up to 10 images simultaneously for premium users.
Each image is optimized and all results are returned in a ZIP archive.
"""

import os
import shutil
import tempfile
import time
import zipfile

from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from src.api.rate_limit_utils import combined_rate_limit

from ...logging_utils import build_request_context, get_logger, log_conversion_start
from ...premium_utils import can_use_batch_processing
from .decorators import optimize_image_docs
from .utils import optimize_image

logger = get_logger(__name__)


class OptimizeImageBatchAPIView(APIView):
    """Handle batch image optimization requests."""

    CONVERSION_TYPE = "optimize_image_batch"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @optimize_image_docs()
    def post(self, request: HttpRequest):
        """Handle batch image optimization with ZIP output."""
        start_time = time.time()
        context = build_request_context(request)
        tmp_dir = None
        tmp_dirs_to_cleanup = set()

        try:
            image_files = request.FILES.getlist("image_files")
            if not image_files:
                return Response(
                    {"error": "No image files provided. Use 'image_files' field name."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            can_batch, error_msg = can_use_batch_processing(
                request.user, len(image_files)
            )
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            # Parse optional params
            try:
                quality = int(request.POST.get("quality", 85))
                quality = max(10, min(100, quality))
            except (ValueError, TypeError):
                quality = 85

            output_format = request.POST.get("output_format", "") or None

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

            log_conversion_start(logger, self.CONVERSION_TYPE, context)

            tmp_dir = tempfile.mkdtemp(prefix="optimize_img_batch_")
            output_files = []

            for idx, image_file in enumerate(image_files):
                try:
                    logger.info(
                        f"Processing file {idx + 1}/{len(image_files)}: {image_file.name}",
                        extra={
                            **context,
                            "file_index": idx,
                            "input_filename": image_file.name,
                        },
                    )

                    input_path, output_path = optimize_image(
                        image_file,
                        quality=quality,
                        output_format=output_format,
                        max_width=max_width,
                        max_height=max_height,
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(output_path))
                    output_files.append((image_file.name, output_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {image_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            zip_path = os.path.join(tmp_dir, "optimize_image_batch.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, out_path in output_files:
                    zip_name = os.path.basename(out_path)
                    zipf.write(out_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="optimize_image_convertica.zip",
            )
            response["Content-Type"] = "application/zip"
            response["X-Convertica-Batch-Count"] = str(len(output_files))
            response["X-Convertica-Duration-Ms"] = str(
                int((time.time() - start_time) * 1000)
            )

            return response

        finally:
            for d in tmp_dirs_to_cleanup:
                shutil.rmtree(d, ignore_errors=True)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
