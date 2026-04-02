"""Batch PDF crop API views."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import crop_pdf_docs
from .utils import crop_pdf


class CropPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF cropping requests."""

    CONVERSION_TYPE = "CROP_PDF_BATCH"
    TMP_PREFIX = "crop_batch_"
    OUTPUT_ZIP_FILENAME = "cropped_pdfs.zip"

    def get_post_params(self, request):
        x = float(request.POST.get("x", 0))
        y = float(request.POST.get("y", 0))
        width_val = request.POST.get("width")
        width = float(width_val) if width_val and str(width_val).strip() else None
        height_val = request.POST.get("height")
        height = float(height_val) if height_val and str(height_val).strip() else None
        pages = request.POST.get("pages", "all")
        scale_to_page_size = (
            request.POST.get("scale_to_page_size", "false").lower() == "true"
        )
        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "pages": pages,
            "scale_to_page_size": scale_to_page_size,
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = crop_pdf(
            uploaded_file=uploaded_file, suffix="_cropped", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_cropped.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @crop_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
