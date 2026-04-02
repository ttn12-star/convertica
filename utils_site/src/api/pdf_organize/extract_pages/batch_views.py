"""Batch PDF page extraction API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import extract_pages_docs
from .utils import extract_pages


class ExtractPagesBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF page extraction requests."""

    CONVERSION_TYPE = "EXTRACT_PAGES_BATCH"
    TMP_PREFIX = "extract_batch_"
    OUTPUT_ZIP_FILENAME = "extracted_pages.zip"

    def get_post_params(self, request):
        return {"pages": request.POST.get("pages", "1")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = extract_pages(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_extracted.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @extract_pages_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
