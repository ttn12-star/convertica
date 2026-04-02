"""Batch PDF flatten API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import flatten_pdf_docs
from .utils import flatten_pdf


class FlattenPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF flatten requests."""

    CONVERSION_TYPE = "FLATTEN_PDF_BATCH"
    TMP_PREFIX = "flatten_batch_"
    OUTPUT_ZIP_FILENAME = "flattened_pdfs.zip"

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = flatten_pdf(
            uploaded_file=uploaded_file, suffix="_flattened"
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_flattened.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @flatten_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
