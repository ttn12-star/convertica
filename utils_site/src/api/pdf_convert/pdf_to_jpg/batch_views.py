"""Batch PDF to JPG conversion API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import pdf_to_jpg_docs
from .utils import convert_pdf_to_jpg


class PDFToJPGBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF → JPG conversion requests."""

    CONVERSION_TYPE = "PDF_TO_JPG_BATCH"
    TMP_PREFIX = "pdf2jpg_batch_"
    OUTPUT_ZIP_FILENAME = "pdf_to_jpg_convertica.zip"

    def get_post_params(self, request):
        return {
            "pages": request.POST.get("pages", "all"),
            "dpi": int(request.POST.get("dpi", 300)),
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = convert_pdf_to_jpg(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        # output_path is already a ZIP of images per PDF page
        return f"{os.path.splitext(original_name)[0]}_images.zip"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_jpg_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
