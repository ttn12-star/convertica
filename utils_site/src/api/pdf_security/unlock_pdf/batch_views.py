"""Batch PDF unlock API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import unlock_pdf


class UnlockPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF unlock requests."""

    CONVERSION_TYPE = "UNLOCK_PDF_BATCH"
    TMP_PREFIX = "unlock_batch_"
    OUTPUT_ZIP_FILENAME = "unlocked_pdfs.zip"

    def get_post_params(self, request):
        return {"password": request.POST.get("password", "")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = unlock_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_unlocked.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(summary="Unlock Pdf (batch, premium)", file_field="pdf_files")
    def post(self, request: HttpRequest):
        return self._process_batch(request)
