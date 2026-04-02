"""Batch PDF to Text conversion API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import pdf_to_text_docs
from .utils import convert_pdf_to_text


class PDFToTextBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF to Text conversion requests."""

    CONVERSION_TYPE = "PDF_TO_TEXT_BATCH"
    TMP_PREFIX = "pdf2text_batch_"
    OUTPUT_ZIP_FILENAME = "pdf_to_text_convertica.zip"

    def get_post_params(self, request):
        return {
            "include_page_numbers": str(
                request.POST.get("include_page_numbers", "false")
            ).lower()
            == "true",
            "preserve_layout": str(request.POST.get("preserve_layout", "false")).lower()
            == "true",
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = convert_pdf_to_text(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_convertica.txt"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_text_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
