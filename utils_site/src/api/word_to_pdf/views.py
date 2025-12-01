# views.py
import os
import shutil
import logging
from typing import Optional

from django.conf import settings
from django.http import FileResponse, HttpRequest
from django.utils.text import get_valid_filename
from django.core.files.uploadedfile import UploadedFile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from src.exceptions import InvalidPDFError, StorageError, ConversionError
from .serializers import WordToPDFSerializer
from .decorators import word_to_pdf_docs
from .utils import convert_word_to_pdf

logger = logging.getLogger(__name__)


class WordToPDFAPIView(APIView):
    """Handle Word (.doc/.docx) → PDF conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".doc", ".docx"}

    @word_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Convert uploaded Word file to PDF and return as FileResponse.

        Args:
            request (HttpRequest): DRF request containing uploaded Word file.

        Returns:
            FileResponse | Response: PDF file stream or JSON error message.
        """
        serializer = WordToPDFSerializer(data=request.FILES or request.POST)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        word_file: Optional[UploadedFile] = serializer.validated_data.get("docx_file")
        if word_file is None:
            return Response({"error": "docx_file is required"}, status=status.HTTP_400_BAD_REQUEST)

        if word_file.size > self.MAX_UPLOAD_SIZE:
            return Response({"error": "File too large."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        content_type = getattr(word_file, "content_type", None)
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            return Response({"error": f"Unsupported content-type: {content_type}"}, status=status.HTTP_400_BAD_REQUEST)

        safe_name = get_valid_filename(os.path.basename(word_file.name))
        _, ext = os.path.splitext(safe_name.lower())
        if ext not in self.ALLOWED_EXTENSIONS:
            return Response(
                {"error": "Only .doc and .docx files are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        tmp_dir = None
        try:
            docx_path, pdf_path = convert_word_to_pdf(word_file, suffix="_convertica")
            tmp_dir = os.path.dirname(docx_path)

            pdf_filename = os.path.basename(pdf_path)
            response = FileResponse(open(pdf_path, "rb"), as_attachment=True, filename=pdf_filename)
            response["Content-Type"] = "application/pdf"
            return response

        except InvalidPDFError as e:
            logger.info(
                "Invalid Word file structure",
                extra={"uploaded_filename": safe_name, "message": str(e)}
            )
            return Response(
                {"error": f"Invalid Word file structure: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except StorageError as e:
            logger.exception(
                "Storage error during Word→PDF conversion",
                extra={"uploaded_filename": safe_name, "filesize": word_file.size, "message": str(e)}
            )
            return Response(
                {"error": f"Internal storage error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except ConversionError as e:
            logger.exception(
                "Conversion error",
                extra={"uploaded_filename": safe_name, "filesize": word_file.size, "message": str(e)}
            )
            return Response(
                {"error": f"Conversion failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            logger.exception(
                "Unexpected error during Word→PDF conversion",
                extra={"uploaded_filename": safe_name, "filesize": word_file.size, "message": str(e)}
            )
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    logger.exception(
                        "Failed to cleanup temp directory",
                        extra={"tmp_dir": tmp_dir}
                    )
