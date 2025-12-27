# views.py

import os
import tempfile

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, HttpResponse
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.response import Response
from src.tasks.pdf_conversion import generic_conversion_task

from ...base_views import BaseConversionAPIView
from .decorators import jpg_to_pdf_docs
from .serializers import JPGToPDFSerializer
from .utils import convert_jpg_to_pdf


class JPGToPDFAPIView(BaseConversionAPIView):
    """Handle JPG/JPEG → PDF conversion requests.

    Supports both single and multiple image files.
    Multiple images will be combined into a single PDF.
    """

    MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "application/octet-stream",
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
    CONVERSION_TYPE = "JPG_TO_PDF"
    FILE_FIELD_NAME = "image_file"

    def get_serializer_class(self):
        return JPGToPDFSerializer

    def get_docs_decorator(self):
        return jpg_to_pdf_docs

    def get_celery_task(self):
        """Get the Celery task function to execute."""
        return generic_conversion_task

    def get(self, request: HttpRequest):
        """Handle GET request - return method not allowed."""
        return Response(
            {"error": "GET method not allowed. Use POST to convert files."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @jpg_to_pdf_docs()
    def post(self, request: HttpRequest):
        """Handle POST request with Swagger documentation.

        Supports multiple files - all images will be combined into one PDF.
        For multiple files, send multiple 'image_file' parameters in the form.
        """
        # Get all files with the same field name (supports multiple files)
        uploaded_files: list[UploadedFile] = request.FILES.getlist(self.FILE_FIELD_NAME)

        if not uploaded_files:
            return Response(
                {"error": f"{self.FILE_FIELD_NAME} is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(uploaded_files) == 1:
            return async_to_sync(self.post_async)(request)

        # Get quality parameter from request (default 85)
        try:
            quality_value = int(request.data.get("quality", 85))
            # Validate range
            quality_value = max(60, min(95, quality_value))
        except (ValueError, TypeError):
            quality_value = 85

        tmp_dir = tempfile.mkdtemp(prefix="jpg2pdf_multi_")
        try:
            pdf_path = os.path.join(tmp_dir, "merged_convertica.pdf")
            c = canvas.Canvas(pdf_path, pagesize=A4)
            page_width, page_height = A4
            margin = 72
            available_width = page_width - (2 * margin)
            available_height = page_height - (2 * margin)

            for idx, uploaded_file in enumerate(uploaded_files):
                safe_name = os.path.basename(uploaded_file.name or f"image_{idx}.jpg")
                image_path = os.path.join(tmp_dir, safe_name)
                with open(image_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                # For high quality (>= 90), use original image directly if possible
                with Image.open(image_path) as img:
                    needs_conversion = img.mode in ("RGBA", "LA", "P")

                    if quality_value >= 90 and not needs_conversion:
                        # Use original image directly without recompression
                        use_path = image_path
                        img_width, img_height = img.size
                    else:
                        # Convert/optimize image with specified quality
                        optimized_path = os.path.join(tmp_dir, f"opt_{safe_name}")
                        if needs_conversion:
                            img = img.convert("RGB")

                        # For high quality, disable chroma subsampling
                        if quality_value >= 90:
                            img.save(
                                optimized_path,
                                "JPEG",
                                quality=quality_value,
                                subsampling=0,
                                optimize=False,
                            )
                        else:
                            img.save(
                                optimized_path,
                                "JPEG",
                                quality=quality_value,
                                optimize=True,
                            )

                        use_path = optimized_path
                        img_width, img_height = img.size

                width_ratio = available_width / img_width
                height_ratio = available_height / img_height
                scale = min(width_ratio, height_ratio)
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                x = margin + (available_width - scaled_width) / 2
                y = margin + (available_height - scaled_height) / 2

                c.drawImage(ImageReader(use_path), x, y, scaled_width, scaled_height)
                if idx < len(uploaded_files) - 1:
                    c.showPage()

            c.save()

            with open(pdf_path, "rb") as fp:
                pdf_bytes = fp.read()

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                'attachment; filename="merged_convertica.pdf"'
            )
            return response
        finally:
            try:
                import shutil

                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    async def perform_conversion(
        self, uploaded_file: UploadedFile, context: dict, **kwargs
    ) -> tuple[str, str]:
        """Perform JPG to PDF conversion.

        This method is kept for compatibility but is not used in the new implementation.
        """
        # Extract quality parameter (default 85)
        try:
            quality_value = int(kwargs.get("quality", 85))
            # Validate range
            quality_value = max(60, min(95, quality_value))
        except (ValueError, TypeError):
            quality_value = 85

        return await convert_jpg_to_pdf(
            uploaded_file, suffix="_convertica", quality=quality_value
        )
