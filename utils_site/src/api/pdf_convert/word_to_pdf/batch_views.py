"""Batch Word to PDF conversion API views."""

import os

from asgiref.sync import async_to_sync
from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import word_to_pdf_docs
from .utils import convert_word_to_pdf


class WordToPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch Word → PDF conversion requests."""

    CONVERSION_TYPE = "WORD_TO_PDF_BATCH"
    FILE_FIELD_NAME = "word_files"
    TMP_PREFIX = "word2pdf_batch_"
    OUTPUT_ZIP_FILENAME = "word_to_pdf_convertica.zip"

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = async_to_sync(convert_word_to_pdf)(
            uploaded_file, suffix="_convertica"
        )
        return os.path.dirname(output_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_convertica.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @word_to_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
