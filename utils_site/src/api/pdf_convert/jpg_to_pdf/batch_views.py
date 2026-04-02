"""Batch JPG to PDF conversion API views."""

import os

from asgiref.sync import async_to_sync
from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import jpg_to_pdf_docs
from .utils import convert_jpg_to_pdf


class JPGToPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch JPG → PDF conversion requests."""

    CONVERSION_TYPE = "JPG_TO_PDF_BATCH"
    FILE_FIELD_NAME = "image_files"
    TMP_PREFIX = "jpg2pdf_batch_"
    OUTPUT_ZIP_FILENAME = "jpg_to_pdf_convertica.zip"

    def get_post_params(self, request):
        try:
            quality = int(request.POST.get("quality", 85))
            quality = max(60, min(95, quality))
        except (ValueError, TypeError):
            quality = 85
        return {"quality": quality}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = async_to_sync(convert_jpg_to_pdf)(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(output_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_convertica.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @jpg_to_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
