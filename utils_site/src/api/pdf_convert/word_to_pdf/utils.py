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
from ...optimization_manager import optimization_manager

logger = get_logger(__name__)

# Magic numbers for DOCX/DOC validation
DOCX_MAGIC = b"PK\x03\x04"
DOC_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


async def convert_word_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> tuple[str, str]:
    """
    Convert DOC/DOCX to PDF using direct implementation.

    Args:
        uploaded_file: Uploaded Word file
        suffix: Suffix for output filename
    """

    from src.api.pdf_convert.word_to_pdf_optimized import convert_word_to_pdf_optimized

    # Use optimized version directly without optimization manager
    return await convert_word_to_pdf_optimized(uploaded_file, suffix=suffix)
