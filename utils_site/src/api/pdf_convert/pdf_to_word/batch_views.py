"""
Batch PDF to Word conversion API views.

Supports processing up to 10 PDF files simultaneously for premium users.
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
from .decorators import pdf_to_word_docs
from .utils import convert_pdf_to_docx

logger = get_logger(__name__)


class PDFToWordBatchAPIView(APIView):
    """Handle batch PDF → DOCX conversion requests."""

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_word_docs()
    def post(self, request: HttpRequest):
        """Handle batch PDF to Word conversion with ZIP output."""
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

            logger.info(
                f"Batch conversion received {len(pdf_files)} files: {[f.name for f in pdf_files]}",
                extra={**context, "file_count": len(pdf_files)},
            )

            can_batch, error_msg = can_use_batch_processing(
                request.user, len(pdf_files)
            )
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            ocr_enabled = (
                str(request.POST.get("ocr_enabled", "false")).lower() == "true"
            )

            log_conversion_start(logger, "PDF_TO_WORD_BATCH", context)

            tmp_dir = tempfile.mkdtemp(prefix="pdf2word_batch_")
            output_files = []
            failures = []

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

                    pdf_path, docx_path = async_to_sync(convert_pdf_to_docx)(
                        pdf_file,
                        suffix="_convertica",
                        ocr_enabled=ocr_enabled,
                    )
                    tmp_dirs_to_cleanup.add(os.path.dirname(docx_path))
                    output_files.append((pdf_file.name, docx_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {pdf_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )
                    failures.append({"filename": pdf_file.name, "error": str(e)})

            if not output_files:
                return Response(
                    {
                        "error": (
                            "Failed to process any files. Some PDFs may be corrupted or unreadable. "
                            "Try re-saving the PDF (Print to PDF) or repairing it, then retry."
                        ),
                        "failures": failures,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            zip_path = os.path.join(tmp_dir, "pdf_to_word_batch.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, docx_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_convertica.docx"
                    zipf.write(docx_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="pdf_to_word_convertica.zip",
            )
            response["Content-Type"] = "application/zip"
            response["X-Convertica-Batch-Count"] = str(len(output_files))
            response["X-Convertica-Batch-Failed-Count"] = str(len(failures))
            response["X-Convertica-Duration-Ms"] = str(
                int((time.time() - start_time) * 1000)
            )

            return response

        finally:
            for d in tmp_dirs_to_cleanup:
                shutil.rmtree(d, ignore_errors=True)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
