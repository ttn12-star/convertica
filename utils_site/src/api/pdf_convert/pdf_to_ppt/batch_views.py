"""Batch PDF to PowerPoint conversion API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import pdf_to_ppt_docs
from .utils import convert_pdf_to_ppt


class PDFToPowerPointBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF → PowerPoint conversion requests."""

    CONVERSION_TYPE = "PDF_TO_PPT_BATCH"
    TMP_PREFIX = "pdf2ppt_batch_"
    OUTPUT_ZIP_FILENAME = "pdf_to_ppt_convertica.zip"

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = convert_pdf_to_ppt(
            uploaded_file, suffix="_convertica"
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_convertica.pptx"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_ppt_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
