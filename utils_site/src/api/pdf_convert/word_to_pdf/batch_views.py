"""
Batch Word to PDF conversion API views.

Supports processing up to 10 Word files simultaneously for premium users.
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
from .decorators import word_to_pdf_docs
from .utils import convert_word_to_pdf

logger = get_logger(__name__)


class WordToPDFBatchAPIView(APIView):
    """Handle batch Word → PDF conversion requests."""

    CONVERSION_TYPE = "WORD_TO_PDF_BATCH"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @word_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle batch Word to PDF conversion with ZIP output."""
        start_time = time.time()
        context = build_request_context(request)
        tmp_dir = None
        tmp_dirs_to_cleanup = set()

        try:
            word_files = request.FILES.getlist("word_files")
            if not word_files:
                return Response(
                    {"error": "No Word files provided. Use 'word_files' field name."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            can_batch, error_msg = can_use_batch_processing(
                request.user, len(word_files)
            )
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            log_conversion_start(logger, "WORD_TO_PDF_BATCH", context)

            tmp_dir = tempfile.mkdtemp(prefix="word2pdf_batch_")
            output_files = []

            for idx, word_file in enumerate(word_files):
                try:
                    logger.info(
                        f"Processing file {idx + 1}/{len(word_files)}: {word_file.name}",
                        extra={
                            **context,
                            "file_index": idx,
                            "input_filename": word_file.name,
                        },
                    )

                    word_path, pdf_path = async_to_sync(convert_word_to_pdf)(
                        word_file,
                        suffix="_convertica",
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(pdf_path))
                    output_files.append((word_file.name, pdf_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {word_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            zip_path = os.path.join(tmp_dir, "word_to_pdf_batch.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, pdf_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_convertica.pdf"
                    zipf.write(pdf_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="word_to_pdf_convertica.zip",
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
