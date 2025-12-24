"""
Batch PDF to HTML conversion API views.

Supports processing up to 10 PDF files simultaneously for premium users.
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
from .decorators import pdf_to_html_docs
from .utils import convert_pdf_to_html

logger = get_logger(__name__)


class PDFToHTMLBatchAPIView(APIView):
    """Handle batch PDF → HTML conversion requests."""

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_html_docs()
    def post(self, request: HttpRequest):
        """Handle batch PDF to HTML conversion with ZIP output."""
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

            log_conversion_start(logger, "PDF_TO_HTML_BATCH", context)

            tmp_dir = tempfile.mkdtemp(prefix="pdf2html_batch_")
            output_files = []

            for idx, pdf_file in enumerate(pdf_files):
                try:
                    pdf_path, html_path = convert_pdf_to_html(
                        pdf_file,
                        suffix="_convertica",
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(pdf_path))
                    output_files.append((pdf_file.name, html_path))

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

            zip_path = os.path.join(tmp_dir, "pdf_to_html_batch.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, html_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_convertica.html"
                    zipf.write(html_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="pdf_to_html_convertica.zip",
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
