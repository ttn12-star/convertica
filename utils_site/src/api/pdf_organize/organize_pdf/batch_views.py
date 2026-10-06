"""Batch PDF organisation API views."""

import json
import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import organize_pdf


class OrganizePDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF organisation requests."""

    CONVERSION_TYPE = "ORGANIZE_PDF_BATCH"
    TMP_PREFIX = "organize_batch_"
    OUTPUT_ZIP_FILENAME = "organized_pdfs.zip"

    def get_post_params(self, request):
        # The JSON string went to organize_pdf() as is: its length never
        # matched the page count, so every reordering batch failed.
        raw = request.POST.get("page_order", "")
        try:
            order = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            order = "invalid"
        return {"page_order": order}

    def validate_single(self, uploaded_file, params):
        order = params.get("page_order")
        if order is not None and not (
            isinstance(order, list)
            and order
            and all(isinstance(i, int) and i >= 0 for i in order)
        ):
            return False, "page_order must be a JSON array of page indices."
        return True, None

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = organize_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_organized.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(summary="Organize Pdf (batch, premium)", file_field="pdf_files")
    def post(self, request: HttpRequest):
        return self._process_batch(request)
