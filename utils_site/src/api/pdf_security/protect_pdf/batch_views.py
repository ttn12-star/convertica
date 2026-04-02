"""Batch PDF protection API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import protect_pdf_docs
from .utils import protect_pdf


class ProtectPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF protection requests."""

    CONVERSION_TYPE = "PROTECT_PDF_BATCH"
    TMP_PREFIX = "protect_batch_"
    OUTPUT_ZIP_FILENAME = "protected_pdfs.zip"

    def get_post_params(self, request):
        return {
            "password": request.POST.get("password", ""),
            "user_password": request.POST.get("user_password"),
            "owner_password": request.POST.get("owner_password"),
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = protect_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_protected.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @protect_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
