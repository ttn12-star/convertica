# views.py
import atexit
import os
import shutil
import time

from django.conf import settings
from django.http import FileResponse, HttpRequest
from rest_framework import status
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
from .decorators import split_pdf_docs
from .serializers import SplitPDFSerializer
from .utils import split_pdf

logger = get_logger(__name__)


class SplitPDFAPIView(APIView):
    """Handle PDF split requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)

    def get_serializer_class(self):
        return SplitPDFSerializer

    @split_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request for splitting PDF."""
        start_time = time.time()
        context = build_request_context(request)

        try:
            serializer = SplitPDFSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid request", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            pdf_file = serializer.validated_data.get("pdf_file")
            split_type = serializer.validated_data.get("split_type", "page")
            pages = serializer.validated_data.get("pages")

            if pdf_file.size > self.MAX_UPLOAD_SIZE:
                max_size_mb = int(self.MAX_UPLOAD_SIZE / (1024 * 1024))
                return Response(
                    {
                        "error": "File too large. Maximum size is %d MB." % max_size_mb
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            log_conversion_start(logger, "SPLIT_PDF", context)

            # Split PDF
            tmp_dir, zip_path = split_pdf(
                pdf_file, split_type=split_type, pages=pages, suffix="_convertica"
            )

            log_conversion_success(
                logger, "SPLIT_PDF", context, start_time, os.path.getsize(zip_path)
            )

            # Return ZIP file
            filename = os.path.basename(zip_path)
            response = FileResponse(
                open(zip_path, "rb"), as_attachment=True, filename=filename
            )
            response["Content-Type"] = "application/zip"

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
                logger, "SPLIT_PDF", context, e, start_time, level="warning"
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (StorageError, ConversionError) as e:
            log_conversion_error(
                logger, "SPLIT_PDF", context, e, start_time, level="exception"
            )
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            log_conversion_error(
                logger, "SPLIT_PDF", context, e, start_time, level="exception"
            )
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
