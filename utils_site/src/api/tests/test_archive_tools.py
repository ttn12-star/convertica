import io
import zipfile

import pyzipper
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from src.exceptions import (
    EncryptedArchiveError,
    EncryptedPDFError,
    InvalidArchiveError,
    InvalidPDFError,
)


def _plain_zip_upload(files, name="docs.zip"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/zip")


def _aes_zip_upload(files, password, name="enc.zip"):
    buf = io.BytesIO()
    with pyzipper.AESZipFile(
        buf, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
    ) as z:
        z.setpassword(password)
        z.setencryption(pyzipper.WZ_AES, nbits=256)
        for n, data in files.items():
            z.writestr(n, data)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/zip")


class ArchiveExceptionsTests(TestCase):
    def test_archive_errors_subclass_pdf_errors_for_400_mapping(self):
        # base_views.handle_conversion_error maps EncryptedPDFError/InvalidPDFError to HTTP 400.
        self.assertTrue(issubclass(EncryptedArchiveError, EncryptedPDFError))
        self.assertTrue(issubclass(InvalidArchiveError, InvalidPDFError))
        self.assertEqual(str(EncryptedArchiveError("nope")), "nope")


class ProtectZipUtilTests(TestCase):
    def test_roundtrip_preserves_files_and_folders(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip

        up = _plain_zip_upload({"a.txt": b"hello", "sub/b.txt": b"world"})
        _, out_path = protect_zip(up, password="s3cret!")
        with pyzipper.AESZipFile(out_path) as z:
            z.setpassword(b"s3cret!")
            self.assertEqual(z.read("a.txt"), b"hello")
            self.assertEqual(z.read("sub/b.txt"), b"world")

    def test_output_requires_password(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip

        up = _plain_zip_upload({"a.txt": b"hello"})
        _, out_path = protect_zip(up, password="s3cret!")
        with pyzipper.AESZipFile(out_path) as z:
            z.setpassword(b"wrong-one")
            with self.assertRaises(RuntimeError):
                z.read("a.txt")

    def test_rejects_already_encrypted(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip

        up = _aes_zip_upload({"a.txt": b"hi"}, password=b"x")
        with self.assertRaises(EncryptedArchiveError):
            protect_zip(up, password="s3cret!")

    def test_rejects_non_zip(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip

        up = SimpleUploadedFile(
            "not.zip",
            b"this is definitely not a zip file",
            content_type="application/zip",
        )
        with self.assertRaises(InvalidArchiveError):
            protect_zip(up, password="s3cret!")

    @override_settings(ARCHIVE_MAX_TOTAL_UNCOMPRESSED=10)
    def test_zip_bomb_guard(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip

        up = _plain_zip_upload({"a.txt": b"hello world this is more than ten bytes"})
        with self.assertRaises(InvalidArchiveError):
            protect_zip(up, password="s3cret!")


class UnlockZipUtilTests(TestCase):
    def test_roundtrip_restores_contents(self):
        from src.api.archive_tools.protect_zip.utils import protect_zip
        from src.api.archive_tools.unlock_zip.utils import unlock_zip

        up = _plain_zip_upload({"a.txt": b"hello", "sub/b.txt": b"world"})
        _, protected_path = protect_zip(up, password="s3cret!")
        with open(protected_path, "rb") as fh:
            protected_upload = SimpleUploadedFile(
                "p.zip", fh.read(), content_type="application/zip"
            )
        _, out_path = unlock_zip(protected_upload, password="s3cret!")
        with zipfile.ZipFile(out_path) as z:
            self.assertEqual(z.read("a.txt"), b"hello")
            self.assertEqual(z.read("sub/b.txt"), b"world")
            self.assertTrue(all(not (zi.flag_bits & 0x1) for zi in z.infolist()))

    def test_wrong_password(self):
        from src.api.archive_tools.unlock_zip.utils import unlock_zip

        up = _aes_zip_upload({"a.txt": b"hi"}, password=b"correct")
        with self.assertRaises(EncryptedArchiveError):
            unlock_zip(up, password="incorrect")

    def test_rejects_unencrypted(self):
        from src.api.archive_tools.unlock_zip.utils import unlock_zip

        up = _plain_zip_upload({"a.txt": b"hi"})
        with self.assertRaises(InvalidArchiveError):
            unlock_zip(up, password="whatever")
