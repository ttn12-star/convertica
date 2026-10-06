"""
Batch PDF watermark API views.

Supports processing up to 10 PDF files simultaneously for premium users.
All files are watermarked with the same parameters and returned as a ZIP archive.
"""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import add_watermark


def _number(request, name, default, kind=float):
    value = request.POST.get(name)
    try:
        return kind(value) if value not in (None, "") else default
    except ValueError:
        return default


class AddWatermarkBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF watermark requests.

    Used to subclass the single-file view, which read the pdf_files list as one
    file (500 "'list' object has no attribute 'name'") and passed parameters
    add_watermark() does not take.
    """

    CONVERSION_TYPE = "ADD_WATERMARK_BATCH"
    TMP_PREFIX = "watermark_batch_"
    OUTPUT_ZIP_FILENAME = "watermarked_pdfs.zip"

    def get_post_params(self, request):
        return {
            "watermark_text": request.POST.get("watermark_text") or "CONFIDENTIAL",
            # Same image for every file: add_watermark() rewinds it each time.
            "watermark_file": request.FILES.get("watermark_file")
            or request.FILES.get("watermark_image"),
            "position": request.POST.get("position") or "diagonal",
            "x": _number(request, "x", None),
            "y": _number(request, "y", None),
            "color": request.POST.get("color") or "#000000",
            "opacity": _number(request, "opacity", 0.3),
            "font_size": _number(request, "font_size", 72, int),
            "rotation": _number(request, "rotation", 0.0),
            "scale": _number(request, "scale", 1.0),
            "pages": request.POST.get("pages") or "all",
        }

    def convert_single(self, uploaded_file, context, **params):
        input_path, output_path = add_watermark(
            uploaded_file, suffix="_watermarked", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_watermarked.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(
        summary="Add Watermark (batch, premium)", file_field="pdf_files"
    )
    def post(self, request: HttpRequest):
        return self._process_batch(request)
