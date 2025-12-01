import os
import subprocess
import tempfile
from typing import Tuple
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
import logging

from src.exceptions import ConversionError, StorageError

logger = logging.getLogger(__name__)


def convert_word_to_pdf(uploaded_file: UploadedFile, suffix: str = "_convertica") -> Tuple[str, str]:
    """Convert DOC/DOCX → PDF using LibreOffice headless mode.

    Args:
        uploaded_file (UploadedFile): Word file (.doc/.docx)
        suffix (str): Suffix to append to output PDF filename.

    Returns:
        Tuple[str, str]: (path to original Word file, path to generated PDF)

    Raises:
        StorageError, ConversionError
    """
    tmp_dir = tempfile.mkdtemp(prefix="doc2pdf_")

    try:
        safe_name = get_valid_filename(os.path.basename(uploaded_file.name))
        docx_path = os.path.join(tmp_dir, safe_name)
        base_name, _ = os.path.splitext(safe_name)
        pdf_name = f"{base_name}{suffix}.pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)

        try:
            with open(docx_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except (OSError, IOError) as err:
            raise StorageError(f"Failed to write Word file to temp: {err}") from err

        logger.info("Starting LibreOffice conversion", extra={"input_file": docx_path, "tmp_dir": tmp_dir})
        try:
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmp_dir,
                    docx_path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout = result.stdout.decode()
            stderr = result.stderr.decode()
            logger.debug("LibreOffice stdout: %s", stdout)
            logger.debug("LibreOffice stderr: %s", stderr)
        except subprocess.CalledProcessError as e:
            raise ConversionError(f"LibreOffice conversion failed: {e.stderr.decode()}") from e

        if not os.path.exists(pdf_path):
            candidates = [f for f in os.listdir(tmp_dir) if f.endswith(".pdf") and f.startswith(base_name)]
            if candidates:
                pdf_path = os.path.join(tmp_dir, candidates[0])
                logger.info("PDF file found after conversion: %s", pdf_path)
            else:
                logger.error("PDF output file not created", extra={"tmp_dir": tmp_dir, "input_file": docx_path})
                raise ConversionError("PDF output file not created.")

        return docx_path, pdf_path

    except Exception:
        raise
