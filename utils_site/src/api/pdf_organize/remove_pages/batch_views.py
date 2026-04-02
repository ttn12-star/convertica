"""Batch PDF page removal API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import remove_pages_docs
from .utils import remove_pages


class RemovePagesBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF page removal requests."""

    CONVERSION_TYPE = "REMOVE_PAGES_BATCH"
    TMP_PREFIX = "remove_batch_"
    OUTPUT_ZIP_FILENAME = "removed_pages.zip"

    def get_post_params(self, request):
        return {"pages": request.POST.get("pages", "")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = remove_pages(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_removed.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @remove_pages_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
