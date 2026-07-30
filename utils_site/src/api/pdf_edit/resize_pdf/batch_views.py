"""Batch PDF page-size API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import resize_pdf


class ResizePDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF page-size change requests."""

    CONVERSION_TYPE = "RESIZE_PDF_BATCH"
    TMP_PREFIX = "resize_batch_"
    OUTPUT_ZIP_FILENAME = "resized_pdfs.zip"
    VALIDATE_PDF_PAGES = False  # Parity with single ResizePDFAPIView

    def get_post_params(self, request: HttpRequest) -> dict:
        return {
            "target_size": request.POST.get("target_size", "letter"),
            "mode": request.POST.get("mode", "auto"),
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = resize_pdf(
            uploaded_file=uploaded_file,
            target_size=params.get("target_size", "letter"),
            mode=params.get("mode", "auto"),
            suffix="_resized",
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_resized.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(
        summary="Change Pdf Page Size (batch, premium)", file_field="pdf_files"
    )
    def post(self, request: HttpRequest):
        return self._process_batch(request)
