"""Batch signing for premium users: one signature image on every PDF, ZIP out."""

import os

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.batch_docs import batch_premium_docs
from src.api.rate_limit_utils import combined_rate_limit

from .utils import apply_simple_signature_to_pdf


class SignPDFBatchAPIView(BaseBatchAPIView):
    """Used to subclass the single-file view, which read the pdf_files list as
    one file: every request was a 500 ("'list' object has no attribute 'name'")."""

    CONVERSION_TYPE = "SIGN_PDF_BATCH"
    TMP_PREFIX = "sign_batch_"
    OUTPUT_ZIP_FILENAME = "signed_pdfs.zip"

    def get_post_params(self, request):
        def number(name, default, kind=int):
            try:
                return kind(request.POST.get(name) or default)
            except ValueError:
                return default

        return {
            # A file param: the async batch stores it in the task dir.
            "signature_image": request.FILES.get("signature_image"),
            "page_number": max(number("page_number", 1) - 1, 0),
            "position": request.POST.get("position") or "bottom-right",
            "signature_width": number("signature_width", 150),
            "opacity": number("opacity", 1.0, float),
            "all_pages": str(request.POST.get("all_pages", "")).lower()
            in ("true", "1", "on"),
        }

    def validate_single(self, uploaded_file, params):
        if params.get("signature_image") is None:
            return False, "A signature image is required."
        return True, None

    def convert_single(self, uploaded_file, context, **params):
        signature = params["signature_image"]
        signature.seek(0)  # the same image signs every PDF
        input_path, output_path = apply_simple_signature_to_pdf(
            pdf_file=uploaded_file, suffix="_signed", **params
        )
        return os.path.dirname(input_path), output_path

    def get_zip_entry_name(self, original_name, output_path):
        return f"{os.path.splitext(original_name)[0]}_signed.pdf"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @batch_premium_docs(summary="Sign Pdf (batch, premium)", file_field="pdf_files")
    def post(self, request: HttpRequest):
        return self._process_batch(request)
