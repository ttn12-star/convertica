"""Batch PDF organisation API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import organize_pdf_docs
from .utils import organize_pdf


class OrganizePDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF organisation requests."""

    CONVERSION_TYPE = "ORGANIZE_PDF_BATCH"
    TMP_PREFIX = "organize_batch_"
    OUTPUT_ZIP_FILENAME = "organized_pdfs.zip"

    def get_post_params(self, request):
        return {"page_order": request.POST.get("page_order", "")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = organize_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_organized.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @organize_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
