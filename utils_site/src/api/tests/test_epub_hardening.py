"""EPUB input-hardening: bad input must be a 400 (InvalidPDFError), and the
ZIP container must be bounded against decompression bombs. Regression cover for
the audit finding that every bad EPUB surfaced as a 500 and reads were
unbounded."""

import io
import zipfile

from django.test import SimpleTestCase, override_settings
from src.api.epub_convert.utils import _parse_epub_structure, _read_member_capped
from src.exceptions import InvalidPDFError


def _write(tmp, data: bytes) -> str:
    path = tmp / "in.epub"
    path.write_bytes(data)
    return str(path)


class EpubHardeningTests(SimpleTestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.tmp = Path(tempfile.mkdtemp())

    def test_non_zip_file_is_400_not_500(self):
        path = _write(self.tmp, b"this is definitely not a zip archive")
        with self.assertRaises(InvalidPDFError):
            _parse_epub_structure(path)

    def test_valid_zip_without_opf_is_400(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("mimetype", "application/epub+zip")
            z.writestr("random.txt", "no opf here")
        path = _write(self.tmp, buf.getvalue())
        with self.assertRaises(InvalidPDFError):
            _parse_epub_structure(path)

    @override_settings(ARCHIVE_MAX_MEMBER_UNCOMPRESSED=16)
    def test_read_member_capped_rejects_oversized_member(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("big.html", "x" * 1000)  # actual bytes far exceed 16-byte cap
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as z, self.assertRaises(InvalidPDFError):
            _read_member_capped(z, "big.html")

    @override_settings(ARCHIVE_MAX_MEMBERS=1)
    def test_too_many_members_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("a", "1")
            z.writestr("b", "2")
        path = _write(self.tmp, buf.getvalue())
        with self.assertRaises(InvalidPDFError):
            _parse_epub_structure(path)
