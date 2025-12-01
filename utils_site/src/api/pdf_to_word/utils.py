# services/convert.py
import os
import tempfile
from typing import Tuple

from pdf2docx import Converter
from django.core.files.uploadedfile import UploadedFile

from src.exceptions import (
    ConversionError,
    EncryptedPDFError,
    InvalidPDFError,
    StorageError,
)


def convert_pdf_to_docx(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Save uploaded PDF to temp, convert it to DOCX and return (pdf_path, docx_path).

    Args:
        uploaded_file (UploadedFile): Uploaded PDF file.
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_pdf, path_to_docx) where docx exists.

    Raises:
        EncryptedPDFError: when the PDF appears to be password-protected.
        InvalidPDFError: when pdf is malformed and conversion fails.
        StorageError: for filesystem I/O errors.
        ConversionError: for other conversion-related failures.
    """
    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix="pdf2docx_")
        safe_name = os.path.basename(uploaded_file.name)
        pdf_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        docx_name = f"{base}{suffix}.docx"
        docx_path = os.path.join(tmp_dir, docx_name)

        try:
            with open(pdf_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as io_err:
            raise StorageError(f"Failed to write uploaded file: {io_err}") from io_err

        try:
            cv = Converter(pdf_path)
            try:
                cv.convert(docx_path)
            finally:
                cv.close()
        except Exception as conv_exc:
            msg = str(conv_exc).lower()
            if "encrypted" in msg or "password" in msg:
                raise EncryptedPDFError("PDF is encrypted/password protected") from conv_exc
            if "error" in msg or "parse" in msg or "format" in msg:
                raise InvalidPDFError(f"Invalid PDF structure: {conv_exc}") from conv_exc
            raise ConversionError(f"Conversion failed: {conv_exc}") from conv_exc

        if not os.path.exists(docx_path):
            raise ConversionError("Conversion finished but DOCX not found")

        return pdf_path, docx_path

    finally:

        pass
