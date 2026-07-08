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

from django.conf import settings
from django.http import FileResponse, HttpRequest
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from src.exceptions import ConversionError, EncryptedPDFError, InvalidPDFError

from .conversion_limits import get_max_file_size_for_user, validate_pdf_pages
from .logging_utils import build_request_context, get_logger, log_conversion_start
from .premium_utils import (
    can_use_batch_processing,
    is_premium_active,
    ocr_premium_gate_message,
)

logger = get_logger(__name__)


class BaseBatchAPIView(APIView):
    """Base class for batch conversion views (multiple files → ZIP)."""

    # Batch endpoints only ever accept multipart file uploads. Mirror
    # BaseConversionAPIView and drop the default JSONParser: with JSONParser
    # present, drf-yasg infers a JSON request body that conflicts with the
    # IN_FORM file parameters and breaks /api/docs/ schema generation.
    parser_classes = [MultiPartParser, FormParser]

    # ── Required class attributes (set in each subclass) ────────────────────
    CONVERSION_TYPE: str = ""
    FILE_FIELD_NAME: str = "pdf_files"
    TMP_PREFIX: str = "batch_"
    OUTPUT_ZIP_FILENAME: str = "batch_output.zip"

    # Mirror BaseConversionAPIView: validate PDF page count for PDF inputs.
    # Set False on tools whose single-file counterpart sets VALIDATE_PDF_PAGES
    # = False, so batch enforcement stays in parity (no over-enforcement).
    VALIDATE_PDF_PAGES: bool = True

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

    # ── Premium-limit parity with the single-file path ───────────────────────
    #
    # The batch endpoint must enforce the same per-file premium limits as
    # BaseConversionAPIView. Without this, a free user can route one oversized /
    # long / OCR-flagged file through /batch/ and bypass the size cap, the PDF
    # page cap and the OCR-premium gate that the single endpoint applies.

    def _operation_key(self) -> str:
        """Normalise CONVERSION_TYPE to the single-path operation key.

        Batch views use a `<OP>_BATCH` CONVERSION_TYPE, but HEAVY_OPERATIONS
        and PREMIUM_PAGE_LIMITS are keyed on the bare lowercase op (e.g.
        ``pdf_to_word``). Strip the suffix so heavy/limit lookups match.
        """
        key = (self.CONVERSION_TYPE or "").lower()
        if key.endswith("_batch"):
            key = key[: -len("_batch")]
        return key

    def _is_pdf_file(self, uploaded_file) -> bool:
        """Check if the uploaded file is a PDF (mirrors BaseConversionAPIView)."""
        name = getattr(uploaded_file, "name", "") or ""
        content_type = getattr(uploaded_file, "content_type", "") or ""
        return name.lower().endswith(".pdf") or "pdf" in content_type.lower()

    def check_ocr_premium(self, request: HttpRequest, params: dict) -> Response | None:
        """Gate OCR behind premium for the batch path (request-level param).

        Returns a 403 Response if OCR was requested by a non-premium user,
        else None. Messages mirror BaseConversionAPIView.post.
        """
        ocr_enabled = params.get("ocr_enabled", False)
        if isinstance(ocr_enabled, str):
            ocr_enabled = ocr_enabled.lower() == "true"
        if not ocr_enabled:
            return None

        payments_enabled = getattr(settings, "PAYMENTS_ENABLED", True)
        error_msg = ocr_premium_gate_message(request.user, payments_enabled)
        if error_msg:
            return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)

        return None

    def validate_premium_limits(
        self, uploaded_file, request: HttpRequest
    ) -> Response | None:
        """Validate one file's size and (for PDFs) page count against the
        requesting user's premium tier. Returns an error Response or None.
        """
        operation = self._operation_key()
        user = request.user

        # File-size cap (mirrors BaseConversionAPIView.validate_file_basic).
        max_file_size = get_max_file_size_for_user(user, operation)
        if uploaded_file.size > max_file_size:
            is_premium = is_premium_active(user)
            free_limit = settings.MAX_FILE_SIZE_FREE
            premium_limit = settings.MAX_FILE_SIZE_PREMIUM
            if not is_premium and uploaded_file.size > free_limit:
                error = _(
                    "File too large (%(file_mb).1f MB). Free users: max "
                    "%(free_mb).0f MB. Upgrade to Premium for %(premium_mb).0f MB limit."
                ) % {
                    "file_mb": uploaded_file.size / (1024 * 1024),
                    "free_mb": free_limit / (1024 * 1024),
                    "premium_mb": premium_limit / (1024 * 1024),
                }
            else:
                error = _("File too large. Maximum size is %(max_mb).0f MB.") % {
                    "max_mb": max_file_size / (1024 * 1024)
                }
            return Response(
                {"error": error}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        # PDF page-count cap (mirrors BaseConversionAPIView.validate_pdf_page_count).
        if self.VALIDATE_PDF_PAGES and self._is_pdf_file(uploaded_file):
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="batch_pagecheck_")
            try:
                with os.fdopen(fd, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                is_valid, error_message, _page_count = validate_pdf_pages(
                    tmp_path, user=user, operation=operation
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                # Rewind so convert_single re-reads the file from the start.
                uploaded_file.seek(0)

            if not is_valid:
                return Response(
                    {"error": error_message}, status=status.HTTP_400_BAD_REQUEST
                )

        return None

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

            # Premium parity: OCR is a premium-only feature on the single path;
            # gate it here too (request-level param) before doing any work.
            ocr_error = self.check_ocr_premium(request, params)
            if ocr_error is not None:
                return ocr_error

            log_conversion_start(logger, self.CONVERSION_TYPE, context)

            tmp_dir = tempfile.mkdtemp(prefix=self.TMP_PREFIX)
            output_files: list[tuple[str, str]] = []
            failed_files: list[tuple[str, str]] = []  # (name, user-safe reason)
            # Mirrors the single-file path contract (handle_conversion_error):
            # bad input (Encrypted/InvalidPDF) is a 400, anything else a 500.
            # Stays True only while every failure is user-input; flips on the
            # first server-side failure so an all-failed batch reports 4xx vs 5xx
            # correctly instead of blanket-500 (which alerts Sentry as an outage).
            all_failures_user_input = True

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

                    # Premium parity: enforce per-file size + PDF page caps
                    # against the requesting user's tier, like the single path.
                    limit_error = self.validate_premium_limits(uploaded_file, request)
                    if limit_error is not None:
                        return limit_error

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
                    is_user_input = isinstance(e, EncryptedPDFError | InvalidPDFError)
                    if not is_user_input:
                        all_failures_user_input = False
                    # User-input failures (bad/encrypted PDF) are expected and
                    # logged at warning; genuine server faults stay at error.
                    log = logger.warning if is_user_input else logger.error
                    log(
                        f"Failed to process {uploaded_file.name}: {e}",
                        extra={**context, "file_index": idx, "error": str(e)},
                    )
                    # ConversionError messages are written to be user-facing
                    # (same contract as the single-file path); anything else
                    # stays generic so internals don't leak into the manifest.
                    reason = (
                        str(e).strip()
                        if isinstance(e, ConversionError) and str(e).strip()
                        else "conversion failed"
                    )
                    failed_files.append(
                        (uploaded_file.name or f"file_{idx + 1}", reason)
                    )

            if not output_files:
                return Response(
                    {
                        "error": "Failed to process any files",
                        "failed_files": [name for name, _reason in failed_files],
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                        if all_failures_user_input
                        else status.HTTP_500_INTERNAL_SERVER_ERROR
                    ),
                )

            zip_path = os.path.join(tmp_dir, self.OUTPUT_ZIP_FILENAME)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for original_name, output_path in output_files:
                    zip_name = self.get_zip_entry_name(original_name, output_path)
                    zipf.write(output_path, zip_name)
                if failed_files:
                    # Name the dropped files inside the archive itself — the
                    # warning toast is easy to miss, the ZIP is what's kept.
                    manifest = "".join(
                        f"{name}: {reason}\n" for name, reason in failed_files
                    )
                    zipf.writestr("conversion_errors.txt", manifest)

            cleanup_targets = list(tmp_dirs_to_cleanup) + [tmp_dir]
            tmp_dirs_to_cleanup = set()
            tmp_dir = None  # ownership transferred to response.close()

            fh = open(zip_path, "rb")  # noqa: SIM115 - lifetime owned by FileResponse
            response = FileResponse(
                fh,
                as_attachment=True,
                filename=self.OUTPUT_ZIP_FILENAME,
            )
            original_close = response.close

            def _close_and_cleanup(_targets=tuple(cleanup_targets)) -> None:
                try:
                    original_close()
                finally:
                    for d in _targets:
                        if d and os.path.isdir(d):
                            shutil.rmtree(d, ignore_errors=True)

            response.close = _close_and_cleanup  # type: ignore[method-assign]
            response["Content-Type"] = "application/zip"
            response["X-Convertica-Batch-Count"] = str(len(output_files))
            # converter.js reads this to warn the user about dropped files.
            response["X-Convertica-Batch-Failed-Count"] = str(len(failed_files))
            response["X-Convertica-Duration-Ms"] = str(
                int((time.time() - start_time) * 1000)
            )
            return response

        finally:
            # Only fires on the error path — success path defers cleanup to
            # response.close() so the ZIP stream isn't yanked mid-flight.
            for d in tmp_dirs_to_cleanup:
                shutil.rmtree(d, ignore_errors=True)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
