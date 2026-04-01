"""
Batch PDF flatten API views.

Supports processing up to 10 PDF files simultaneously for premium users.
All files are flattened (form fields and annotations removed) and returned as a ZIP archive.
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
from .decorators import flatten_pdf_docs
from .utils import flatten_pdf

logger = get_logger(__name__)


class FlattenPDFBatchAPIView(APIView):
    """Handle batch PDF flatten requests for premium users."""

    CONVERSION_TYPE = "FLATTEN_PDF_BATCH"
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_EXTENSIONS = {".pdf"}

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @flatten_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle batch PDF flatten with ZIP output."""
        start_time = time.time()
        context = build_request_context(request)
        tmp_dir = None
        tmp_dirs_to_cleanup = set()

        try:
            pdf_files = request.FILES.getlist("pdf_files")

            if not pdf_files:
                return Response(
                    {"error": "No PDF files provided. Use 'pdf_files' field name."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            can_batch, error_msg = can_use_batch_processing(
                request.user, len(pdf_files)
            )
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            log_conversion_start(logger, "FLATTEN_PDF_BATCH", context)

            tmp_dir = tempfile.mkdtemp(prefix="flatten_batch_")
            output_files = []

            for idx, pdf_file in enumerate(pdf_files):
                try:
                    logger.info(
                        f"Processing file {idx + 1}/{len(pdf_files)}: {pdf_file.name}",
                        extra={
                            **context,
                            "file_index": idx,
                            "input_filename": pdf_file.name,
                        },
                    )

                    input_path, output_path = flatten_pdf(
                        uploaded_file=pdf_file,
                        suffix="_flattened",
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(input_path))
                    output_files.append((pdf_file.name, output_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {pdf_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            zip_path = os.path.join(tmp_dir, "flattened_pdfs.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, output_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_flattened.pdf"
                    zipf.write(output_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="flattened_pdfs.zip",
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
