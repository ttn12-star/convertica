"""
Batch Excel to PDF conversion API views.

Supports processing up to 20 Excel files simultaneously for premium users.
Uses async processing for better performance with multiple files.
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
from ...premium_utils import can_use_batch_processing, is_premium_active
from .decorators import excel_to_pdf_docs
from .utils import convert_excel_to_pdf, validate_excel_file

logger = get_logger(__name__)


class ExcelToPDFBatchAPIView(APIView):
    """Handle batch Excel → PDF conversion requests."""

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @excel_to_pdf_docs()
    def post(self, request: HttpRequest):
        start_time = time.time()
        context = build_request_context(request)

        if not is_premium_active(request.user):
            return Response(
                {"error": "Batch conversion is a premium feature."},
                status=status.HTTP_403_FORBIDDEN,
            )

        excel_files = request.FILES.getlist("excel_files")
        if not excel_files:
            return Response(
                {"error": "No Excel files provided. Use 'excel_files' field name."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        can_batch, error_msg = can_use_batch_processing(request.user, len(excel_files))
        if not can_batch:
            return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

        log_conversion_start(logger, "EXCEL_TO_PDF_BATCH", context)

        tmp_dir = tempfile.mkdtemp(prefix="excel2pdf_batch_")
        tmp_dirs_to_cleanup: set[str] = set()
        output_files: list[tuple[str, str]] = []

        try:
            for idx, excel_file in enumerate(excel_files):
                is_valid, err = validate_excel_file(excel_file)
                if not is_valid:
                    return Response(
                        {"error": err or "Invalid Excel file"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                input_path, output_path = async_to_sync(convert_excel_to_pdf)(
                    excel_file, suffix="_convertica"
                )
                tmp_dirs_to_cleanup.add(os.path.dirname(input_path))
                output_files.append((excel_file.name, output_path))

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            zip_path = os.path.join(tmp_dir, "converted_excels.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_index, (original_name, pdf_path) in enumerate(
                    output_files, start=1
                ):
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = (
                        os.path.basename(pdf_path) or f"{base_name}_convertica.pdf"
                    )
                    if zip_name in zipf.namelist():
                        zip_name = f"{base_name}_{file_index}_convertica.pdf"
                    zipf.write(pdf_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="excel_to_pdf_convertica.zip",
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
            shutil.rmtree(tmp_dir, ignore_errors=True)
