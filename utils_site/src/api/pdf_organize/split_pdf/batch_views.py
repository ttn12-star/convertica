"""Batch PDF split API views."""

from django.http import HttpRequest
from src.api.base_batch_views import BaseBatchAPIView
from src.api.rate_limit_utils import combined_rate_limit

from .decorators import split_pdf_docs
from .utils import split_pdf


class SplitPDFBatchAPIView(BaseBatchAPIView):
    """Handle batch PDF split requests."""

    CONVERSION_TYPE = "SPLIT_PDF_BATCH"
    TMP_PREFIX = "split_batch_"
    OUTPUT_ZIP_FILENAME = "split_pdfs.zip"

    def get_post_params(self, request):
        return {
            "split_type": request.POST.get("split_type", "page"),
            "pages": request.POST.get("pages"),
        }

    def convert_single(self, uploaded_file, context, **params):
        # split_pdf returns (file_tmp_dir, zip_path) — add the dir directly to cleanup
        file_tmp_dir, zip_path = split_pdf(
            uploaded_file, suffix="_convertica", **params
        )
        return file_tmp_dir, zip_path

    def get_zip_entry_name(self, original_name, output_path):
        # output_path is a per-file ZIP of individual pages
        return f"{original_name.rsplit('.', 1)[0]}_split.zip"

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    @split_pdf_docs()
    def post(self, request: HttpRequest):
        return self._process_batch(request)
