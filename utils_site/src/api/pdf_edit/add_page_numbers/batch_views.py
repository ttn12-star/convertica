"""Batch page numbering for premium users: same settings for every PDF, ZIP out."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import add_page_numbers

# Older clients send the batch serializer's "format" choice instead of format_str.
_FORMATS = {"number": "{page}", "page_of_total": "Page {page} of {total}"}


class AddPageNumbersBatchAPIView(BaseBatchAPIView):
    """Used to subclass the single-file view, which read the pdf_files list as
    one file (500 "'list' object has no attribute 'name'") and passed
    arguments add_page_numbers() does not take."""

    CONVERSION_TYPE = "ADD_PAGE_NUMBERS_BATCH"
    TMP_PREFIX = "page_numbers_batch_"
    OUTPUT_ZIP_FILENAME = "numbered_pdfs.zip"

    def get_post_params(self, request):
        def number(name, default):
            try:
                return int(request.POST.get(name) or default)
            except ValueError:
                return default

        return {
            "position": request.POST.get("position") or "bottom-center",
            "font_size": number("font_size", 12),
            "start_number": number("start_number", 1),
            "format_str": request.POST.get("format_str")
            or _FORMATS.get(request.POST.get("format"), "{page}"),
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = add_page_numbers(
            uploaded_file, suffix="_numbered", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_numbered.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(
        summary="Add Page Numbers (batch, premium)", file_field="pdf_files"
    )
    def post(self, request: HttpRequest):
        return self._process_batch(request)
