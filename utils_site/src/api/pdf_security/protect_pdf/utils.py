import os

from django.core.files.uploadedfile import UploadedFile
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


def protect_pdf(
    uploaded_file: UploadedFile,
    password: str,
    user_password: str = None,
    owner_password: str = None,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Protect PDF with password encryption.

    Args:
        uploaded_file: PDF file to protect
        password: Password for both user and owner (if user_password/owner_password not provided)
        user_password: User password (optional, uses password if not provided)
        owner_password: Owner password (optional, uses password if not provided)
        permissions: PDF permissions (bit flags), -1 for all permissions
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)
    """
    context = {
        "function": "protect_pdf",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }

    try:
        # Validate passwords
        if not password or not password.strip():
            raise ConversionError("Password cannot be empty", context=context)

        if len(password.strip()) < 1:
            raise ConversionError(
                "Password must be at least 1 character long", context=context
            )

        processor = BasePDFProcessor(
            uploaded_file,
            tmp_prefix="protect_pdf_",
            required_mb=200,
            context=context,
        )
        pdf_path = processor.prepare()

        # Check if PDF is already encrypted
        try:
            test_reader = PdfReader(pdf_path)
            if test_reader.is_encrypted:
                raise EncryptedPDFError(
                    "PDF is already password-protected. Please unlock it first or use a different PDF.",
                    context=context,
                )
        except EncryptedPDFError:
            raise
        except Exception:
            pass

        # Determine passwords
        user_pwd = (
            user_password.strip()
            if user_password and user_password.strip()
            else password.strip()
        )
        owner_pwd = (
            owner_password.strip()
            if owner_password and owner_password.strip()
            else password.strip()
        )

        # Validate optional passwords if provided
        if user_password and len(user_password.strip()) < 1:
            raise ConversionError(
                "User password must be at least 1 character long", context=context
            )
        if owner_password and len(owner_password.strip()) < 1:
            raise ConversionError(
                "Owner password must be at least 1 character long", context=context
            )

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_name = "%s_protected%s.pdf" % (base, suffix)
        output_path = os.path.join(processor.tmp_dir, output_name)
        context["output_path"] = output_path

        def _op(
            input_pdf_path: str, *, output_path: str, user_pwd: str, owner_pwd: str
        ):
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            try:
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
            except Exception:
                pass
            writer.encrypt(
                user_password=user_pwd,
                owner_password=owner_pwd,
                use_128bit=True,
            )
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path

        processor.run_pdf_operation_with_repair(
            _op,
            output_path=output_path,
            user_pwd=user_pwd,
            owner_pwd=owner_pwd,
        )
        processor.validate_output_pdf_allow_encrypted(output_path, min_size=1000)
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
