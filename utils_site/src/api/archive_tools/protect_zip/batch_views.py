import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import protect_zip_docs
from .utils import protect_zip


class ProtectZipBatchAPIView(BaseBatchAPIView):
    """Handle batch Protect ZIP requests (premium)."""

    CONVERSION_TYPE = "PROTECT_ZIP_BATCH"
    FILE_FIELD_NAME = "archive_files"
    TMP_PREFIX = "protect_zip_batch_"
    OUTPUT_ZIP_FILENAME = "protected_archives.zip"
    VALIDATE_PDF_PAGES = False

    def get_post_params(self, request):
        return {"password": request.POST.get("password", "")}

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = protect_zip(
            uploaded_file, suffix="_convertica", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_protected.zip"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @protect_zip_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
