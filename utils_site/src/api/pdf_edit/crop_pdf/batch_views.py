"""
Batch PDF cropping API views.

Supports processing up to 10 PDF files simultaneously for premium users.
All files are cropped with the same parameters and returned as a ZIP archive.
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
from .decorators import crop_pdf_docs
from .utils import crop_pdf

logger = get_logger(__name__)


class CropPDFBatchAPIView(APIView):
    """Handle batch PDF cropping requests for premium users."""

    CONVERSION_TYPE = "CROP_PDF_BATCH"
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB per file
    ALLOWED_EXTENSIONS = {".pdf"}

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @crop_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle batch PDF cropping with ZIP output."""
        start_time = time.time()
        context = build_request_context(request)
        tmp_dir = None

        try:
            # Get all PDF files
            pdf_files = request.FILES.getlist("pdf_files")

            if not pdf_files:
                return Response(
                    {"error": "No PDF files provided. Use 'pdf_files' field name."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check premium status and batch limits
            can_batch, error_msg = can_use_batch_processing(
                request.user, len(pdf_files)
            )
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            # Get crop parameters
            x = float(request.POST.get("x", 0))
            y = float(request.POST.get("y", 0))
            width_val = request.POST.get("width")
            width = float(width_val) if width_val and str(width_val).strip() else None
            height_val = request.POST.get("height")
            height = (
                float(height_val) if height_val and str(height_val).strip() else None
            )
            pages = request.POST.get("pages", "all")
            scale_to_page_size = (
                request.POST.get("scale_to_page_size", "false").lower() == "true"
            )

            log_conversion_start(logger, "CROP_PDF_BATCH", context)

            # Create temp directory for processing
            tmp_dir = tempfile.mkdtemp(prefix="crop_batch_")
            output_files = []

            # Process each PDF
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

                    input_path, output_path = crop_pdf(
                        uploaded_file=pdf_file,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        pages=pages,
                        scale_to_page_size=scale_to_page_size,
                        suffix="_cropped",
                    )

                    output_files.append((pdf_file.name, output_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {pdf_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )
                    # Continue processing other files

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create ZIP archive
            zip_path = os.path.join(tmp_dir, "cropped_pdfs.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, output_path in output_files:
                    base_name = os.path.splitext(original_name)[0]
                    zip_name = f"{base_name}_cropped.pdf"
                    zipf.write(output_path, zip_name)

            # Return ZIP file
            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="cropped_pdfs.zip",
            )
            response["Content-Type"] = "application/zip"

            logger.info(
                f"Batch crop completed: {len(output_files)}/{len(pdf_files)} files",
                extra={
                    **context,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "files_processed": len(output_files),
                },
            )

            return response

        except Exception as e:
            logger.exception(
                "Batch crop failed",
                extra={**context, "error": str(e)},
            )
            return Response(
                {"error": f"Batch processing failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
