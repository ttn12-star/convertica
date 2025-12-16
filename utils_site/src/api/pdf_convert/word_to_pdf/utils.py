import os
import subprocess
import tempfile

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename

from ....exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)
from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_word_file,
)
from ...logging_utils import get_logger

logger = get_logger(__name__)

# Magic numbers for DOCX/DOC validation
DOCX_MAGIC = b"PK\x03\x04"
DOC_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _check_libreoffice_available() -> bool:
    """Check if LibreOffice is installed and available."""
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def _validate_magic_number(uploaded_file: UploadedFile) -> None:
    """Quickly validate Word file magic number before writing."""
    try:
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        if header.startswith(DOCX_MAGIC) or header.startswith(DOC_MAGIC):
            return
        else:
            raise InvalidPDFError("File does not appear to be a valid Word document")
    except Exception as e:
        raise InvalidPDFError(f"Failed to validate Word file: {e}") from e


def convert_word_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Convert DOC/DOCX → PDF using LibreOffice headless mode (optimized)."""

    tmp_dir = tempfile.mkdtemp(prefix="doc2pdf_")

    original_filename = uploaded_file.name if uploaded_file.name else "unknown"
    safe_name = sanitize_filename(
        get_valid_filename(os.path.basename(original_filename))
    )

    # Ensure proper extension
    if not safe_name.lower().endswith((".doc", ".docx")):
        original_ext = os.path.splitext(original_filename)[1].lower()
        if original_ext in (".doc", ".docx"):
            safe_name = os.path.splitext(safe_name)[0] + original_ext

    context = {
        "function": "convert_word_to_pdf",
        "input_filename": safe_name,
        "original_filename": original_filename,
        "input_size": uploaded_file.size,
        "tmp_dir": tmp_dir,
    }

    try:
        # Quick magic number check before writing
        _validate_magic_number(uploaded_file)

        # Check if LibreOffice is available
        if not _check_libreoffice_available():
            logger.error(
                "LibreOffice is not available",
                extra={**context, "event": "libreoffice_not_found"},
            )
            raise ConversionError(
                "LibreOffice is not installed or not available in PATH", context=context
            )

        # Check disk space before writing
        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        docx_path = os.path.join(tmp_dir, safe_name)
        base_name, _ = os.path.splitext(safe_name)
        pdf_name = f"{base_name}{suffix}.pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)

        context.update({"docx_path": docx_path, "pdf_path": pdf_path})

        # Write uploaded file to temp in controlled chunks
        try:
            logger.debug(
                "Writing Word file to temporary location",
                extra={**context, "event": "file_write_start"},
            )
            with open(docx_path, "wb") as f:
                for chunk in uploaded_file.chunks(
                    chunk_size=512 * 1024
                ):  # 512 KB chunks
                    f.write(chunk)
            logger.debug(
                "File written successfully",
                extra={**context, "event": "file_write_success"},
            )
        except OSError as err:
            logger.error(
                "Failed to write Word file to temp",
                extra={**context, "event": "file_write_error", "error": str(err)},
                exc_info=True,
            )
            raise StorageError(
                f"Failed to write Word file to temp: {err}",
                context={**context, "error_type": type(err).__name__},
            ) from err

        # Validate Word file after writing
        is_valid, validation_error = validate_word_file(docx_path, context)
        if not is_valid:
            raise InvalidPDFError(
                validation_error or "Invalid Word file structure", context=context
            )

        # Perform LibreOffice conversion
        logger.info(
            "Starting LibreOffice conversion",
            extra={**context, "event": "conversion_start"},
        )
        try:
            env = os.environ.copy()
            env["SAL_DEFAULT_PAPER"] = "A4"
            env["SAL_DISABLE_CUPS"] = "1"

            pdf_filter_params = (
                "UseTaggedPDF=0,SelectPdfVersion=1,Quality=100,"
                "MaxImageResolution=300,EmbedStandardFonts=1"
            )

            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--nodefault",
                    "--nolockcheck",
                    "--nologo",
                    "--norestore",
                    "--invisible",
                    "--convert-to",
                    f"pdf:writer_pdf_Export:{pdf_filter_params}",
                    "--outdir",
                    tmp_dir,
                    docx_path,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
                cwd=tmp_dir,
                env=env,
            )
            stdout = result.stdout.decode("utf-8", errors="ignore")
            stderr = result.stderr.decode("utf-8", errors="ignore")
            logger.debug(
                "LibreOffice conversion completed",
                extra={
                    **context,
                    "event": "libreoffice_complete",
                    "stdout": stdout[:200],
                    "stderr": stderr[:200],
                },
            )
        except subprocess.TimeoutExpired as e:
            raise ConversionError(
                "LibreOffice conversion timed out after 10 minutes",
                context={**context, "error_type": "TimeoutExpired"},
            ) from e
        except subprocess.CalledProcessError as e:
            stderr = (
                e.stderr.decode("utf-8", errors="ignore")
                if e.stderr
                else "Unknown error"
            )
            if "password" in stderr.lower() or "protected" in stderr.lower():
                raise ConversionError(
                    "Word file is password-protected and cannot be converted",
                    context={**context, "error_type": "ProtectedFile"},
                ) from e
            raise ConversionError(
                f"LibreOffice conversion failed: {stderr[:200]}",
                context={**context, "error_type": "CalledProcessError"},
            ) from e

        # Verify output PDF exists
        if not os.path.exists(pdf_path):
            pdf_files = [f for f in os.listdir(tmp_dir) if f.endswith(".pdf")]
            if pdf_files:
                preferred = [f for f in pdf_files if f.startswith(base_name)]
                found_file = preferred[0] if preferred else pdf_files[0]
                pdf_path = os.path.join(tmp_dir, found_file)
                logger.info(
                    "PDF file found with alternative name",
                    extra={
                        **context,
                        "event": "pdf_found_alternative",
                        "found_filename": found_file,
                    },
                )
            else:
                raise ConversionError(
                    "PDF output file not created. LibreOffice conversion may have failed.",
                    context=context,
                )

        # Validate output PDF
        is_valid, validation_error = validate_output_file(
            pdf_path, min_size=500, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output PDF file is invalid", context=context
            )

        output_size = os.path.getsize(pdf_path)
        logger.info(
            "Word to PDF conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
            },
        )

        return docx_path, pdf_path

    except (StorageError, ConversionError, InvalidPDFError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during Word to PDF conversion",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
