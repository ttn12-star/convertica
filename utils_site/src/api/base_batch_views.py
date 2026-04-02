"""
Base class for batch file conversion API views (multiple files → ZIP archive).

All 21 old-pattern batch views follow the same structure:
  1. Collect files from request.FILES.getlist(FILE_FIELD_NAME)
  2. Check can_use_batch_processing()
  3. Convert each file via convert_single()
  4. Pack results into a ZIP archive
  5. Return FileResponse(zip)

Subclasses must implement:
  - convert_single(uploaded_file, context, **params) → (cleanup_dir, output_path)
  - CONVERSION_TYPE, FILE_FIELD_NAME, TMP_PREFIX, OUTPUT_ZIP_FILENAME class attrs

Subclasses may override:
  - get_post_params(request) → dict   : extract tool-specific POST params
  - get_zip_entry_name(orig, out)     : filename inside the ZIP
  - validate_single(file, params)     : per-file pre-conversion validation
  - post(request)                     : to apply per-tool docs decorator
"""

import os
import shutil
import tempfile
import time
import zipfile
from abc import abstractmethod

from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .logging_utils import build_request_context, get_logger, log_conversion_start
from .premium_utils import can_use_batch_processing

logger = get_logger(__name__)


class BaseBatchAPIView(APIView):
    """Base class for batch conversion views (multiple files → ZIP)."""

    # ── Required class attributes (set in each subclass) ────────────────────
    CONVERSION_TYPE: str = ""
    FILE_FIELD_NAME: str = "pdf_files"
    TMP_PREFIX: str = "batch_"
    OUTPUT_ZIP_FILENAME: str = "batch_output.zip"

    # ── Hooks (override as needed) ───────────────────────────────────────────

    def get_post_params(self, request: HttpRequest) -> dict:
        """Extract tool-specific parameters from request.POST. Override as needed."""
        return {}

    def validate_single(self, uploaded_file, params: dict) -> tuple[bool, str | None]:
        """Validate a single file before conversion.

        Return (True, None) to proceed, or (False, error_message) to abort the
        entire batch with HTTP 400.
        """
        return True, None

    @abstractmethod
    def convert_single(self, uploaded_file, context: dict, **params) -> tuple[str, str]:
        """Convert a single uploaded file.

        Returns:
            (cleanup_dir, output_path) where:
              cleanup_dir  – temp directory to add to the cleanup set
              output_path  – converted output file to include in the ZIP
        """
        raise NotImplementedError

    def get_zip_entry_name(self, original_name: str, output_path: str) -> str:
        """Return the filename to use inside the output ZIP archive.

        Default: use the output file's basename (includes the converter suffix).
        Override in subclasses for a cleaner or different name.
        """
        return os.path.basename(output_path)

    # ── Core batch logic (call from subclass post()) ─────────────────────────

    def _process_batch(self, request: HttpRequest) -> Response:
        """Run the full batch pipeline. Call this from the subclass post() method."""
        start_time = time.time()
        context = build_request_context(request)
        tmp_dir = None
        tmp_dirs_to_cleanup: set[str] = set()

        try:
            files = request.FILES.getlist(self.FILE_FIELD_NAME)
            if not files:
                return Response(
                    {
                        "error": (
                            f"No files provided. Use '{self.FILE_FIELD_NAME}' field name."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            can_batch, error_msg = can_use_batch_processing(request.user, len(files))
            if not can_batch:
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

            params = self.get_post_params(request)
            log_conversion_start(logger, self.CONVERSION_TYPE, context)

            tmp_dir = tempfile.mkdtemp(prefix=self.TMP_PREFIX)
            output_files: list[tuple[str, str]] = []

            for idx, uploaded_file in enumerate(files):
                try:
                    logger.info(
                        f"Processing file {idx + 1}/{len(files)}: {uploaded_file.name}",
                        extra={
                            **context,
                            "file_index": idx,
                            "input_filename": uploaded_file.name,
                        },
                    )

                    is_valid, err = self.validate_single(uploaded_file, params)
                    if not is_valid:
                        return Response(
                            {"error": err or "Invalid file"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    cleanup_dir, output_path = self.convert_single(
                        uploaded_file, context, **params
                    )
                    tmp_dirs_to_cleanup.add(cleanup_dir)
                    output_files.append((uploaded_file.name, output_path))

                except Exception as e:
                    logger.error(
                        f"Failed to process {uploaded_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )

            if not output_files:
                return Response(
                    {"error": "Failed to process any files"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            zip_path = os.path.join(tmp_dir, self.OUTPUT_ZIP_FILENAME)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, output_path in output_files:
                    zip_name = self.get_zip_entry_name(original_name, output_path)
                    zipf.write(output_path, zip_name)

            response = FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename=self.OUTPUT_ZIP_FILENAME,
            )
            response["Content-Type"] = "application/zip"
            response["X-Convertica-Batch-Count"] = str(len(output_files))
            response["X-Convertica-Duration-Ms"] = str(
                int((time.time() - start_time) * 1000)
            )
            return response

        finally:
            for d in tmp_dirs_to_cleanup:
                shutil.rmtree(d, ignore_errors=True)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
