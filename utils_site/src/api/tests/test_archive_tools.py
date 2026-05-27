import io
import zipfile

import pyzipper
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
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


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ProtectUnlockZipAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.client.defaults["HTTP_REFERER"] = "https://convertica.net/"

    @staticmethod
    def _read_response(resp):
        """Return the full body of a regular or streaming response."""
        if getattr(resp, "streaming", False):
            return b"".join(resp.streaming_content)
        return resp.content

    def test_protect_zip_api_returns_zip(self):
        raw = _plain_zip_upload({"a.txt": b"hello"}).read()
        upload = SimpleUploadedFile("docs.zip", raw, content_type="application/zip")
        resp = self.client.post(
            reverse("protect_zip_api"),
            data={"archive_file": upload, "password": "s3cret!"},
        )
        body = self._read_response(resp)
        self.assertEqual(resp.status_code, 200, body[:500])
        self.assertEqual(resp["Content-Type"], "application/zip")
        self.assertEqual(body[:2], b"PK")  # zip magic

    def test_protect_zip_api_rejects_non_zip_extension(self):
        upload = SimpleUploadedFile("note.txt", b"x" * 200, content_type="text/plain")
        resp = self.client.post(
            reverse("protect_zip_api"),
            data={"archive_file": upload, "password": "s3cret!"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_unlock_zip_api_wrong_password_400(self):
        raw = _aes_zip_upload({"a.txt": b"hi"}, password=b"correct").read()
        upload = SimpleUploadedFile("enc.zip", raw, content_type="application/zip")
        resp = self.client.post(
            reverse("unlock_zip_api"),
            data={"archive_file": upload, "password": "incorrect"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_unlock_zip_api_roundtrip(self):
        raw = _plain_zip_upload({"a.txt": b"hello"}).read()
        protect_resp = self.client.post(
            reverse("protect_zip_api"),
            data={
                "archive_file": SimpleUploadedFile(
                    "docs.zip", raw, content_type="application/zip"
                ),
                "password": "s3cret!",
            },
        )
        protected = self._read_response(protect_resp)
        self.assertEqual(protect_resp.status_code, 200, protected[:500])
        # Clear the request-timing cache entry so the second call isn't throttled.
        cache.clear()
        unlock_resp = self.client.post(
            reverse("unlock_zip_api"),
            data={
                "archive_file": SimpleUploadedFile(
                    "p.zip", protected, content_type="application/zip"
                ),
                "password": "s3cret!",
            },
        )
        unlock_body = self._read_response(unlock_resp)
        self.assertEqual(unlock_resp.status_code, 200, unlock_body[:500])
