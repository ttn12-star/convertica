"""Batch PDF compression API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import compress_pdf_docs
from .utils import compress_pdf


class CompressPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF compression requests."""

    CONVERSION_TYPE = "COMPRESS_PDF_BATCH"
    TMP_PREFIX = "compress_batch_"
    OUTPUT_ZIP_FILENAME = "compressed_pdfs.zip"

    def get_post_params(self, request):
        return {"compression_level": request.POST.get("compression_level", "medium")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = compress_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_compressed.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @compress_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
