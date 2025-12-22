import os

from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext as _
from PyPDF2 import PdfReader, PdfWriter
from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)

from ...logging_utils import get_logger
from ...pdf_processing import BasePDFProcessor

logger = get_logger(__name__)


def unlock_pdf(
    uploaded_file: UploadedFile, password: str, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Unlock PDF by removing password protection.

    Args:
        uploaded_file: Password-protected PDF file
        password: Password to unlock the PDF
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "unlock_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }

    try:
        # Validate password
        if not password or not password.strip():
            raise EncryptedPDFError(_("Password cannot be empty"), context=context)

        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="unlock_pdf_",
            required_mb=200,
            context=context,
            allow_encrypted_input=True,
        )
        pdf_path = processor.prepare()

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = "%s_unlocked%s.pdf" % (base, suffix)
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _op(input_pdf_path: str, *, output_path: str, password: str):
            reader = PdfReader(input_pdf_path)
            if not reader.is_encrypted:
                raise InvalidPDFError(
                    _(
                        "PDF is not password-protected. This PDF does not require a password to open."
                    ),
                    context=context,
                )

            decrypt_result = reader.decrypt(password)
            if not decrypt_result:
                raise EncryptedPDFError(
                    _("Incorrect password. Please check the password and try again."),
                    context=context,
                )

            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            try:
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
            except Exception:
                pass

            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            password=password,
        )

        processor.validate_output_pdf(output_path, min_size=1000)
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
