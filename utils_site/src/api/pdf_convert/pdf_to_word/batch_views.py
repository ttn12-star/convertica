"""Batch PDF to Word conversion API views."""

import os

from asgiref.sync import async_to_sync
from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import pdf_to_word_docs
from .utils import convert_pdf_to_docx


class PDFToWordBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF → DOCX conversion requests."""

    CONVERSION_TYPE = "PDF_TO_WORD_BATCH"
    TMP_PREFIX = "pdf2word_batch_"
    OUTPUT_ZIP_FILENAME = "pdf_to_word_convertica.zip"

    def get_post_params(self, request):
        return {
            "ocr_enabled": str(request.POST.get("ocr_enabled", "false")).lower()
            == "true"
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = async_to_sync(convert_pdf_to_docx)(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(output_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_convertica.docx"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @pdf_to_word_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
