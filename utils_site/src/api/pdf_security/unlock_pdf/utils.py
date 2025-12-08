# utils.py
import os
import tempfile
from typing import Tuple

from django.core.files.uploadedfile import UploadedFile
from PyPDF2 import PdfReader, PdfWriter
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
)
from ...logging_utils import get_logger
from ...pdf_utils import repair_pdf

logger = get_logger(__name__)


def unlock_pdf(
    uploaded_file: UploadedFile, password: str, suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Unlock PDF by removing password protection.

    Args:
        uploaded_file: Password-protected PDF file
        password: Password to unlock the PDF
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "unlock_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
    }

    try:
        tmp_dir = tempfile.mkdtemp(prefix="unlock_pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        output_name = "%s_unlocked%s.pdf" % (base, suffix)
        output_path = os.path.join(tmp_dir, output_name)

        context.update({"pdf_path": pdf_path, "output_path": output_path})

        # Write uploaded file
        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as io_err:
            raise StorageError(
                "Failed to write PDF: %s" % io_err, context=context
            ) from io_err

        # Validate password
        if not password or not password.strip():
            raise EncryptedPDFError("Password cannot be empty", context=context)

        # Validate PDF file first
        is_valid, validation_error = validate_pdf_file(pdf_path, context)
        if not is_valid:
            raise InvalidPDFError(
                validation_error or "Invalid PDF file", context=context
            )

        # Check if PDF is encrypted and unlock
        try:
            logger.info(
                "Starting PDF unlock", extra={**context, "event": "unlock_start"}
            )

            reader = PdfReader(pdf_path)

            # Check if PDF is encrypted
            if not reader.is_encrypted:
                raise InvalidPDFError(
                    "PDF is not password-protected. This PDF does not require a password to open.",
                    context=context,
                )

            # Try to decrypt with provided password
            decrypt_result = reader.decrypt(password)
            if not decrypt_result:
                raise EncryptedPDFError(
                    "Incorrect password. Please check the password and try again.",
                    context=context,
                )

            writer = PdfWriter()

            total_pages = len(reader.pages)
            context["total_pages"] = total_pages

            # Copy all pages (now decrypted)
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    writer.add_page(page)
                except Exception as page_error:
                    logger.warning(
                        "Failed to copy page %d" % page_num,
                        extra={
                            **context,
                            "page_num": page_num,
                            "error": str(page_error),
                        },
                    )
                    # Continue with other pages
                    continue

            # Copy metadata if available
            try:
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
            except Exception as metadata_error:
                logger.warning(
                    "Could not copy metadata",
                    extra={**context, "error": str(metadata_error)},
                )
                # Metadata copy failure is not critical

            # Write unlocked PDF (without encryption)
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.debug(
                "Unlock completed", extra={**context, "event": "unlock_complete"}
            )

        except EncryptedPDFError:
            raise
        except Exception as e:
            error_context = {
                **context,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                "PDF unlock failed",
                extra={**error_context, "event": "unlock_error"},
                exc_info=True,
            )
            raise ConversionError(
                "Failed to unlock PDF: %s" % e, context=error_context
            ) from e

        # Validate output
        is_valid, validation_error = validate_output_file(
            output_path, min_size=1000, context=context
        )
        if not is_valid:
            raise ConversionError(
                validation_error or "Output PDF is invalid", context=context
            )

        output_size = os.path.getsize(output_path)
        logger.info(
            "PDF unlock successful",
            extra={
                **context,
                "event": "unlock_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return pdf_path, output_path

    except (EncryptedPDFError, InvalidPDFError, StorageError, ConversionError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            "Unexpected error: %s" % e,
            context={**context, "error_type": type(e).__name__},
        ) from e
