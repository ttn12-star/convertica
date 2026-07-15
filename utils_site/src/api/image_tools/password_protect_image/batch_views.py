"""Batch password-protect-image API view (premium)."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import protect_image


class PasswordProtectImageBatchAPIView(BaseBatchAPIView):
    """Each uploaded image → its own password-protected PDF, zipped."""

    CONVERSION_TYPE = "PASSWORD_PROTECT_IMAGE_BATCH"
    FILE_FIELD_NAME = "image_files"
    TMP_PREFIX = "protect_image_batch_"
    OUTPUT_ZIP_FILENAME = "protected_images.zip"

    def get_post_params(self, request):
        return {
            "password": request.POST.get("password", ""),
            "user_password": request.POST.get("user_password"),
            "owner_password": request.POST.get("owner_password"),
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = protect_image([uploaded_file], **params)
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_protected.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(
        summary="Password Protect Image (batch, premium)", file_field="image_files"
    )
    def post(self, request: HttpRequest):
        return self._process_batch(request)
