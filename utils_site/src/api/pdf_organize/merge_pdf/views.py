# views.py
import atexit
import os
import shutil
import time

from django.conf import settings
from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import (
    build_request_context,
    get_logger,
    log_conversion_error,
    log_conversion_start,
    log_conversion_success,
)
from .decorators import merge_pdf_docs
from .utils import merge_pdf

logger = get_logger(__name__)


class MergePDFAPIView(APIView):
    """Handle PDF merge requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    parser_classes = [MultiPartParser, FormParser]

    # Don't define get_serializer_class to prevent drf-yasg from auto-detecting request_body
    # We handle validation manually in the post method

    @merge_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request for merging PDFs."""
        start_time = time.time()
        context = build_request_context(request)

        try:
            # Handle multiple file uploads
            # Django's request.FILES.getlist() is the standard way to get multiple files
            # with the same field name from FormData
            pdf_files_list = []

            if "pdf_files" in request.FILES:
                # Standard Django way - getlist() returns all files with the same name
                pdf_files_list = list(request.FILES.getlist("pdf_files"))
                logger.debug(
                    "Got files from request.FILES",
                    extra={
                        **context,
                        "num_files": len(pdf_files_list),
                        "file_names": [f.name for f in pdf_files_list],
                    },
                )
            else:
                # Fallback - check request.data (for DRF)
                logger.warning(
                    "No files in request.FILES, checking request.data",
                    extra=context,
                )
                if hasattr(request, "data") and "pdf_files" in request.data:
                    pdf_files = (
                        request.data.getlist("pdf_files")
                        if hasattr(request.data, "getlist")
                        else request.data.get("pdf_files", [])
                    )
                    if isinstance(pdf_files, list):
                        pdf_files_list = pdf_files
                    else:
                        pdf_files_list = [pdf_files] if pdf_files else []

            # Log for debugging
            logger.info(
                "Received merge request",
                extra={
                    **context,
                    "num_files_received": len(pdf_files_list),
                    "file_names": (
                        [f.name for f in pdf_files_list] if pdf_files_list else []
                    ),
                },
            )

            if len(pdf_files_list) < 2:
                return Response(
                    {"error": "At least 2 PDF files are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(pdf_files_list) > 10:
                return Response(
                    {"error": "Maximum 10 PDF files allowed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get order parameter
            order = "upload"
            if hasattr(request, "data"):
                order = request.data.get("order", "upload")
            elif hasattr(request, "POST"):
                order = request.POST.get("order", "upload")

            pdf_files = pdf_files_list

            # Log files to merge
            logger.info(
                "Files ready for merge",
                extra={
                    **context,
                    "num_files": len(pdf_files),
                    "file_names": [f.name for f in pdf_files],
                    "order": order,
                },
            )

            # Check total size
            total_size = sum(f.size for f in pdf_files)
            if total_size > self.MAX_UPLOAD_SIZE * len(pdf_files):
                return Response(
                    {"error": "Total file size exceeds limit"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            log_conversion_start(logger, "MERGE_PDF", context)

            # Merge PDFs
            tmp_dir, output_path = merge_pdf(
                pdf_files, order=order, suffix="_convertica"
            )

            log_conversion_success(
                logger, "MERGE_PDF", context, start_time, os.path.getsize(output_path)
            )

            # Return file
            filename = os.path.basename(output_path)
            response = FileResponse(
                open(output_path, "rb"), as_attachment=True, filename=filename
            )
            response["Content-Type"] = "application/pdf"

            # Cleanup after response is sent
            def cleanup():
                if tmp_dir and os.path.isdir(tmp_dir):
                    try:
                        shutil.rmtree(tmp_dir)
                    except Exception:
                        pass

            atexit.register(cleanup)

            return response

        except (EncryptedPDFError, InvalidPDFError) as e:
            log_conversion_error(
                logger, "MERGE_PDF", context, e, start_time, level="warning"
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (StorageError, ConversionError) as e:
            log_conversion_error(
                logger, "MERGE_PDF", context, e, start_time, level="exception"
            )
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            log_conversion_error(
                logger, "MERGE_PDF", context, e, start_time, level="exception"
            )
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
