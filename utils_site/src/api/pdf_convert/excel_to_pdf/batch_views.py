"""Batch Excel to PDF conversion API views."""

import os

from asgiref.sync import async_to_sync
from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import excel_to_pdf_docs
from .utils import convert_excel_to_pdf, validate_excel_file


class ExcelToPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch Excel → PDF conversion requests."""

    CONVERSION_TYPE = "EXCEL_TO_PDF_BATCH"
    FILE_FIELD_NAME = "excel_files"
    TMP_PREFIX = "excel2pdf_batch_"
    OUTPUT_ZIP_FILENAME = "excel_to_pdf_convertica.zip"

    def validate_single(self, uploaded_file, params):
        is_valid, err = validate_excel_file(uploaded_file)
        if not is_valid:
            return False, err or "Invalid Excel file"
        return True, None

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = async_to_sync(convert_excel_to_pdf)(
            uploaded_file, suffix="_convertica"
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        base_name = os.path.splitext(original_name)[0]
        return os.path.basename(output_path) or f"{base_name}_convertica.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @excel_to_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
