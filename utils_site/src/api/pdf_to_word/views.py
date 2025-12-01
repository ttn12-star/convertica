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
from src.exceptions import (
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
    ConversionError,
)
from .serializers import PDFToWordSerializer
from .decorators import pdf_to_word_docs
from .utils import convert_pdf_to_docx


logger = logging.getLogger(__name__)


class PDFToWordAPIView(APIView):
    """Handle PDF → DOCX conversion requests."""

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}

    @pdf_to_word_docs()
    def post(self, request: HttpRequest):
        """Convert uploaded PDF to DOCX and stream back the result."""
        serializer = PDFToWordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pdf_file: Optional[UploadedFile] = serializer.validated_data.get("pdf_file")
        if pdf_file is None:
            return Response({"error": "pdf_file is required"}, status=status.HTTP_400_BAD_REQUEST)

        if pdf_file.size > self.MAX_UPLOAD_SIZE:
            return Response({"error": "File too large."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        content_type: Optional[str] = getattr(pdf_file, "content_type", None)
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            return Response({"error": "Unsupported content-type."}, status=status.HTTP_400_BAD_REQUEST)

        safe_name = get_valid_filename(os.path.basename(pdf_file.name))
        _, ext = os.path.splitext(safe_name.lower())
        if ext not in self.ALLOWED_EXTENSIONS:
            return Response({"error": "Only .pdf files are allowed."}, status=status.HTTP_400_BAD_REQUEST)

        tmp_dir = None
        try:
            # call service
            pdf_path, docx_path = convert_pdf_to_docx(pdf_file, suffix="_convertica")
            tmp_dir = os.path.dirname(pdf_path)

            # stream file
            docx_filename = os.path.basename(docx_path)
            response = FileResponse(open(docx_path, "rb"), as_attachment=True, filename=docx_filename)
            response["Content-Type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return response

        except EncryptedPDFError as e:
            logger.warning("Encrypted PDF", extra={"filename": safe_name, "msg": str(e)})
            return Response({"error": "PDF is password-protected and cannot be converted."}, status=status.HTTP_400_BAD_REQUEST)

        except InvalidPDFError as e:
            logger.info("Invalid PDF structure", extra={"filename": safe_name, "msg": str(e)})
            return Response({"error": "Invalid PDF structure."}, status=status.HTTP_400_BAD_REQUEST)

        except StorageError as e:
            logger.exception("Storage error during conversion", extra={"filename": safe_name, "filesize": pdf_file.size})
            return Response({"error": "Internal storage error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except ConversionError as e:
            logger.exception("Conversion error", extra={"filename": safe_name, "filesize": pdf_file.size})
            return Response({"error": "Conversion failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            # last resort
            logger.exception("Unexpected error", extra={"filename": safe_name, "filesize": pdf_file.size})
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # cleanup temporary files if created
            if tmp_dir and os.path.isdir(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    logger.exception("Failed to cleanup temp directory", extra={"tmp_dir": tmp_dir})
