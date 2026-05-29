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

logger = get_logger(__name__)

ENCRYPTED_FLAG = (
    0x1  # ZIP general-purpose bit 0 → entry is encrypted (ZipCrypto or AES)
)


def guard_against_zip_bomb(infos, context: dict) -> None:
    """Reject archives whose declared uncompressed size/members exceed safe limits."""
    max_members = getattr(settings, "ARCHIVE_MAX_MEMBERS", 2000)
    max_member = getattr(settings, "ARCHIVE_MAX_MEMBER_UNCOMPRESSED", 200 * 1024 * 1024)
    max_total = getattr(settings, "ARCHIVE_MAX_TOTAL_UNCOMPRESSED", 500 * 1024 * 1024)

    if len(infos) > max_members:
        raise InvalidArchiveError(
            _("Archive has too many files. Please use a smaller archive."),
            context=context,
        )
    total = 0
    for zi in infos:
        if zi.file_size > max_member:
            raise InvalidArchiveError(
                _("A file inside the archive is too large to process."),
                context=context,
            )
        total += zi.file_size
    if total > max_total:
        raise InvalidArchiveError(
            _("Archive contents are too large to process."),
            context=context,
        )


def read_member_capped(zin, zi, max_member, max_remaining, context: dict) -> bytes:
    """Decompress one ZIP member, aborting if its ACTUAL size exceeds limits.

    ``guard_against_zip_bomb`` only checks the declared ``file_size`` from the
    central directory, which an attacker controls. A crafted member can declare
    a small size yet expand far beyond it; ``zin.read(name)`` would happily
    decompress the whole thing into RAM and OOM-kill the worker. Streaming with
    a running byte count stops decompression as soon as the real output crosses
    the per-member or remaining-total cap.
    """
    cap = min(max_member, max_remaining)
    out = bytearray()
    # Open by name (not the ZipInfo object): callers may pass a ZipInfo from a
    # different ZipFile used only for inspection (e.g. unlock_zip checks the
    # archive with a plain zipfile, then reads members from a pyzipper handle).
    with zin.open(zi.filename) as src:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            out.extend(chunk)
            if len(out) > cap:
                raise InvalidArchiveError(
                    _("Archive contents are too large to process."),
                    context=context,
                )
    return bytes(out)


def protect_zip(
    uploaded_file: UploadedFile, password: str, suffix: str = "_convertica"
) -> tuple[str, str]:
    """Encrypt an uploaded .zip with AES-256 using `password`.

    Returns (input_path, output_path); both live in the same temp dir.
    """
    context = {
        "function": "protect_zip",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
    }
    tmp_dir = tempfile.mkdtemp(prefix="protect_zip_")
    try:
        input_path = os.path.join(tmp_dir, "input.zip")
        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
                f.write(chunk)

        base = os.path.splitext(os.path.basename(uploaded_file.name))[0] or "archive"
        output_path = os.path.join(tmp_dir, "%s_protected%s.zip" % (base, suffix))

        try:
            with zipfile.ZipFile(input_path) as zin:
                infos = zin.infolist()
                if any(zi.flag_bits & ENCRYPTED_FLAG for zi in infos):
                    raise EncryptedArchiveError(
                        _(
                            "This archive is already password-protected. "
                            "Use the 'Unlock ZIP' tool first if you want to change the password."
                        ),
                        context=context,
                    )
                guard_against_zip_bomb(infos, context)

                with pyzipper.AESZipFile(
                    output_path,
                    "w",
                    compression=pyzipper.ZIP_DEFLATED,
                    encryption=pyzipper.WZ_AES,
                ) as zout:
                    zout.setpassword(password.encode("utf-8"))
                    zout.setencryption(pyzipper.WZ_AES, nbits=256)
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
        except zipfile.BadZipFile as e:
            raise InvalidArchiveError(
                _("The uploaded file is not a valid ZIP archive."), context=context
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
