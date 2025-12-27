import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from .file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from .pdf_utils import execute_with_repair_fallback, repair_pdf


def validate_pdf_allow_encrypted(pdf_path: str, *, context: dict) -> None:
    """Minimal PDF validation that allows encrypted PDFs.

    validate_pdf_file() rejects encrypted PDFs by design. For flows like unlock,
    we still want to ensure the file is a PDF and has pages.
    """

    try:
        with open(pdf_path, "rb") as f:
            header = f.read(4)
        if not header.startswith(b"%PDF"):
            raise InvalidPDFError(
                "File does not appear to be a valid PDF (missing PDF header)",
                context=context,
            )

        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path, strict=False)
        if len(reader.pages) == 0:
            raise InvalidPDFError("PDF has no pages", context=context)
    except (EncryptedPDFError, InvalidPDFError):
        raise
    except Exception as e:
        raise InvalidPDFError(
            f"Invalid PDF file: {e}",
            context=context,
        ) from e


class BasePDFProcessor:
    def __init__(
        self,
        uploaded_file: UploadedFile,
        *,
        tmp_prefix: str,
        required_mb: int,
        context: dict,
        allow_encrypted_input: bool = False,
    ):
        self.uploaded_file = uploaded_file
        self.tmp_prefix = tmp_prefix
        self.required_mb = required_mb
        self.context = context
        self.allow_encrypted_input = allow_encrypted_input

        self.tmp_dir: str | None = None
        self.input_path: str | None = None

    def prepare(self) -> str:
        self.tmp_dir = tempfile.mkdtemp(prefix=self.tmp_prefix)
        self.context["tmp_dir"] = self.tmp_dir

        disk_check, disk_error = check_disk_space(
            self.tmp_dir, required_mb=self.required_mb
        )
        if not disk_check:
            raise StorageError(
                disk_error or "Insufficient disk space", context=self.context
            )

        safe_name = sanitize_filename(os.path.basename(self.uploaded_file.name))
        self.input_path = os.path.join(self.tmp_dir, safe_name)
        self.context["pdf_path"] = self.input_path

        try:
            with open(self.input_path, "wb") as f:
                for chunk in self.uploaded_file.chunks():
                    f.write(chunk)
        except OSError as err:
            raise StorageError(
                f"Failed to write PDF: {err}", context=self.context
            ) from err

        if self.allow_encrypted_input:
            validate_pdf_allow_encrypted(self.input_path, context=self.context)
        else:
            is_valid, validation_error = validate_pdf_file(
                self.input_path, self.context
            )
            if not is_valid:
                msg = validation_error or "Invalid PDF file"
                lowered = msg.lower()
                if "password" in lowered or "encrypted" in lowered:
                    raise EncryptedPDFError(msg, context=self.context)
                raise InvalidPDFError(msg, context=self.context)

        return self.input_path

    def run_pdf_operation_with_repair(self, operation_func, *args, **kwargs):
        if not self.input_path:
            raise ConversionError("Processor not prepared", context=self.context)
        return execute_with_repair_fallback(
            self.input_path,
            operation_func,
            self.context,
            *args,
            **kwargs,
        )

    def validate_output_pdf(self, output_path: str, *, min_size: int = 1000) -> None:
        self._validate_output_exists(output_path, min_size=min_size)
        self._validate_output_pdf_structure(output_path, allow_encrypted=False)

    def validate_output_pdf_allow_encrypted(
        self, output_path: str, *, min_size: int = 1000
    ) -> None:
        self._validate_output_exists(output_path, min_size=min_size)
        self._validate_output_pdf_structure(output_path, allow_encrypted=True)

    def _validate_output_exists(self, output_path: str, *, min_size: int) -> None:
        is_valid, validation_error = validate_output_file(
            output_path,
            min_size=min_size,
            context=self.context,
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output file is invalid",
                context=self.context,
            )

    def _validate_output_pdf_structure(
        self, output_path: str, *, allow_encrypted: bool
    ):
        """Validate the output PDF is readable.

        validate_output_file() only checks existence/size. This method ensures
        the file is a readable PDF. If it fails, we try repair_pdf() once.
        """

        def _check(path: str) -> None:
            from PyPDF2 import PdfReader

            reader = PdfReader(path, strict=False)
            if reader.is_encrypted and not allow_encrypted:
                raise EncryptedPDFError(
                    "Output PDF is password-protected", context=self.context
                )
            if len(reader.pages) == 0:
                raise ConversionError("Output PDF has no pages", context=self.context)

        try:
            _check(output_path)
            return
        except Exception:
            repair_pdf(output_path, output_path)
            _check(output_path)


class BasePDFMultiProcessor:
    def __init__(
        self,
        uploaded_files: list[UploadedFile],
        *,
        tmp_prefix: str,
        required_mb: int,
        context: dict,
        allow_encrypted_input: bool = False,
    ):
        self.uploaded_files = uploaded_files
        self.tmp_prefix = tmp_prefix
        self.required_mb = required_mb
        self.context = context
        self.allow_encrypted_input = allow_encrypted_input

        self.tmp_dir: str | None = None
        self.input_paths: list[str] = []

    def prepare(self) -> list[str]:
        self.tmp_dir = tempfile.mkdtemp(prefix=self.tmp_prefix)
        self.context["tmp_dir"] = self.tmp_dir

        disk_check, disk_error = check_disk_space(
            self.tmp_dir, required_mb=self.required_mb
        )
        if not disk_check:
            raise StorageError(
                disk_error or "Insufficient disk space", context=self.context
            )

        self.input_paths = []

        for idx, uploaded_file in enumerate(self.uploaded_files):
            safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
            safe_name = sanitize_filename(f"{idx}_{safe_name}")
            input_path = os.path.join(self.tmp_dir, safe_name)

            try:
                with open(input_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
            except OSError as err:
                raise StorageError(
                    f"Failed to write PDF: {err}",
                    context=self.context,
                ) from err

            # Validate each input
            if self.allow_encrypted_input:
                validate_pdf_allow_encrypted(input_path, context=self.context)
            else:
                is_valid, validation_error = validate_pdf_file(input_path, self.context)
                if not is_valid:
                    msg = validation_error or "Invalid PDF file"
                    lowered = msg.lower()
                    if "password" in lowered or "encrypted" in lowered:
                        raise EncryptedPDFError(msg, context=self.context)
                    raise InvalidPDFError(msg, context=self.context)

            self.input_paths.append(input_path)

        return self.input_paths

    def validate_output_pdf(self, output_path: str, *, min_size: int = 1000) -> None:
        BasePDFProcessor(
            self.uploaded_files[0],
            tmp_prefix="_noop_",
            required_mb=0,
            context=self.context,
        ).validate_output_pdf(output_path, min_size=min_size)
