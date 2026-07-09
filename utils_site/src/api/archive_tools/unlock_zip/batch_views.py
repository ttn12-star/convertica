import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import unlock_zip


class UnlockZipBatchAPIView(BaseBatchAPIView):
    """Handle batch Unlock ZIP requests (premium)."""

    CONVERSION_TYPE = "UNLOCK_ZIP_BATCH"
    FILE_FIELD_NAME = "archive_files"
    TMP_PREFIX = "unlock_zip_batch_"
    OUTPUT_ZIP_FILENAME = "unlocked_archives.zip"
    VALIDATE_PDF_PAGES = False

    def get_post_params(self, request):
        return {"password": request.POST.get("password", "")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = unlock_zip(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_unlocked.zip"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(
        summary="Unlock Zip (batch, premium)", file_field="archive_files"
    )
    def post(self, request: HttpRequest):
        return self._process_batch(request)
