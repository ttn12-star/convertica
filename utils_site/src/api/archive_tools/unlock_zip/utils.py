import os
import shutil
import tempfile
import zipfile

import pyzipper
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext as _
from src.exceptions import (
    ConversionError,
    EncryptedArchiveError,
    InvalidArchiveError,
    StorageError,
)

from ...logging_utils import get_logger
from ..protect_zip.utils import (
    ENCRYPTED_FLAG,
    guard_against_zip_bomb,
    read_member_capped,
)

logger = get_logger(__name__)


def unlock_zip(
    uploaded_file: UploadedFile, password: str, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Remove the password from an encrypted .zip, returning a plain .zip.

    Reads AES and legacy ZipCrypto entries. Returns (input_path, output_path).
    """
    context = {
        "function": "unlock_zip",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }
    tmp_dir = tempfile.mkdtemp(prefix="unlock_zip_")
    try:
        input_path = os.path.join(tmp_dir, "input.zip")
        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                f.write(chunk)

        base = os.path.splitext(os.path.basename(uploaded_file.name))[0] or "archive"
        output_path = os.path.join(tmp_dir, "%s_unlocked%s.zip" % (base, suffix))

        try:
            with zipfile.ZipFile(input_path) as zcheck:
                infos = zcheck.infolist()
                if not any(zi.flag_bits & ENCRYPTED_FLAG for zi in infos):
                    raise InvalidArchiveError(
                        _(
                            "This archive is not password-protected. "
                            "There is nothing to unlock."
                        ),
                        context=context,
                    )
                guard_against_zip_bomb(infos, context)
        except zipfile.BadZipFile as e:
            raise InvalidArchiveError(
                _("The uploaded file is not a valid ZIP archive."), context=context
            ) from e

        try:
            with pyzipper.AESZipFile(input_path) as zin:
                zin.setpassword(password.encode("utf-8"))
                with zipfile.ZipFile(
                    output_path, "w", compression=zipfile.ZIP_DEFLATED
                ) as zout:
                    max_member = getattr(
                        settings, "ARCHIVE_MAX_MEMBER_UNCOMPRESSED", 200 * 1024 * 1024
                    )
                    remaining = getattr(
                        settings, "ARCHIVE_MAX_TOTAL_UNCOMPRESSED", 500 * 1024 * 1024
                    )
                    for zi in infos:
                        if zi.is_dir():
                            zout.writestr(zi.filename, b"")
                            continue
                        data = read_member_capped(
                            zin, zi, max_member, remaining, context
                        )
                        remaining -= len(data)
                        zout.writestr(zi.filename, data)
        except (RuntimeError, zipfile.BadZipFile) as e:
            raise EncryptedArchiveError(
                _("Incorrect password. Please check the password and try again."),
                context=context,
            ) from e

        return input_path, output_path

    except (EncryptedArchiveError, InvalidArchiveError, StorageError, ConversionError):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
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
