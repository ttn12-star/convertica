# views.py
import os
import time
import shutil
import atexit
from typing import Tuple, List

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import MergePDFSerializer
from .decorators import merge_pdf_docs
from .utils import merge_pdf
from ...logging_utils import get_logger, build_request_context, log_conversion_start, log_conversion_success, log_conversion_error
from ...file_validation import check_disk_space
from src.exceptions import ConversionError, StorageError, InvalidPDFError, EncryptedPDFError

logger = get_logger(__name__)


class MergePDFAPIView(APIView):
    """Handle PDF merge requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)

    def get_serializer_class(self):
        return MergePDFSerializer

    @merge_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request for merging PDFs."""
        start_time = time.time()
        context = build_request_context(request)
        
        try:
            # Handle multiple file uploads
            pdf_files_list = request.FILES.getlist('pdf_files') if 'pdf_files' in request.FILES else []
            
            if len(pdf_files_list) < 2:
                return Response(
                    {"error": "At least 2 PDF files are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(pdf_files_list) > 10:
                return Response(
                    {"error": "Maximum 10 PDF files allowed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create serializer data manually for ListField
            serializer_data = {
                'pdf_files': pdf_files_list,
                'order': request.data.get('order', 'upload')
            }
            
            serializer = MergePDFSerializer(data=serializer_data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid request", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            pdf_files = serializer.validated_data.get('pdf_files', [])
            order = serializer.validated_data.get('order', 'upload')
            
            # Check total size
            total_size = sum(f.size for f in pdf_files)
            if total_size > self.MAX_UPLOAD_SIZE * len(pdf_files):
                return Response(
                    {"error": f"Total file size exceeds limit"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            
            log_conversion_start(logger, "MERGE_PDF", context)
            
            # Merge PDFs
            tmp_dir, output_path = merge_pdf(pdf_files, order=order, suffix="_convertica")
            
            log_conversion_success(logger, "MERGE_PDF", context, start_time, os.path.getsize(output_path))
            
            # Return file
            filename = os.path.basename(output_path)
            response = FileResponse(
                open(output_path, 'rb'),
                as_attachment=True,
                filename=filename
            )
            response['Content-Type'] = 'application/pdf'
            
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
            log_conversion_error(logger, "MERGE_PDF", context, e, start_time, level="warning")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (StorageError, ConversionError) as e:
            log_conversion_error(logger, "MERGE_PDF", context, e, start_time, level="exception")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            log_conversion_error(logger, "MERGE_PDF", context, e, start_time, level="exception")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

