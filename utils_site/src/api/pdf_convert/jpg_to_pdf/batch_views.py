"""
Batch JPG to PDF conversion API views.

Supports processing up to 10 JPG files simultaneously for premium users.
Each JPG file is converted to a separate PDF.
"""

import os
import shutil
import tempfile
import time
import zipfile

from asgiref.sync import async_to_sync
from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from src.api.rate_limit_utils import combined_rate_limit

from ...logging_utils import build_request_context, get_logger, log_conversion_start
from ...premium_utils import can_use_batch_processing
from .decorators import jpg_to_pdf_docs
from .utils import convert_jpg_to_pdf

logger = get_logger(__name__)


class JPGToPDFBatchAPIView(APIView):
    """Handle batch JPG → PDF conversion requests."""

    CONVERSION_TYPE = "JPG_TO_PDF_BATCH"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @jpg_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle batch JPG to PDF conversion with ZIP output."""
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

            quality = int(request.POST.get("quality", 85))
            quality = max(60, min(95, quality))

            log_conversion_start(logger, "JPG_TO_PDF_BATCH", context)

            tmp_dir = tempfile.mkdtemp(prefix="jpg2pdf_batch_")
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

                    jpg_path, pdf_path = async_to_sync(convert_jpg_to_pdf)(
                        image_file,
                        suffix="_convertica",
                        quality=quality,
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(pdf_path))
                    output_files.append((image_file.name, pdf_path))

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

            zip_path = os.path.join(tmp_dir, "jpg_to_pdf_batch.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, pdf_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_convertica.pdf"
                    zipf.write(pdf_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="jpg_to_pdf_convertica.zip",
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
