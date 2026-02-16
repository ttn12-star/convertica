"""
Integration tests for API endpoints.
"""

import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    RATELIMIT_ENABLE=False,
    CELERY_BROKER_URL="memory://",
    CELERY_RESULT_BACKEND="cache+memory://",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    LOGGING={
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "root": {"handlers": ["null"]},
    },
)
class APIEndpointsTestCase(TestCase):
    """Integration tests for conversion API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_pdf(self) -> SimpleUploadedFile:
        """Create a minimal valid PDF file for testing."""
        # Minimal valid PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF"""
        return SimpleUploadedFile(
            "test.pdf", pdf_content, content_type="application/pdf"
        )

    def _create_test_image(self) -> SimpleUploadedFile:
        """Create a minimal valid JPG file for testing."""
        # Minimal valid JPEG (just header, not a real image)
        # In real tests, you'd use a proper image file
        jpg_content = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"
        )
        return SimpleUploadedFile("test.jpg", jpg_content, content_type="image/jpeg")

    def _create_test_pdf_with_jpeg(self) -> SimpleUploadedFile:
        from io import BytesIO

        from PIL import Image
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        # Make a reasonably large JPEG so compression has something to work with
        img = Image.new("RGB", (2500, 2500), color=(200, 200, 200))
        img_buf = BytesIO()
        img.save(img_buf, format="JPEG", quality=95)
        img_buf.seek(0)

        pdf_buf = BytesIO()
        c = canvas.Canvas(pdf_buf, pagesize=letter)
        c.drawImage(ImageReader(img_buf), 0, 0, width=612, height=792)
        c.showPage()
        c.save()

        return SimpleUploadedFile(
            "image.pdf", pdf_buf.getvalue(), content_type="application/pdf"
        )

    def _create_test_text_pdf(
        self, text: str = "Convertica test page for PDF to EPUB"
    ) -> SimpleUploadedFile:
        from io import BytesIO

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_buf = BytesIO()
        c = canvas.Canvas(pdf_buf, pagesize=letter)
        c.drawString(72, 720, text)
        c.showPage()
        c.save()
        return SimpleUploadedFile(
            "text.pdf", pdf_buf.getvalue(), content_type="application/pdf"
        )

    def _create_test_epub(self) -> SimpleUploadedFile:
        epub_buffer = io.BytesIO()
        with zipfile.ZipFile(epub_buffer, "w") as archive:
            archive.writestr(
                "mimetype",
                "application/epub+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            archive.writestr(
                "META-INF/container.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
                compress_type=zipfile.ZIP_DEFLATED,
            )
            archive.writestr(
                "OEBPS/content.opf",
                """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Convertica Test Book</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
""",
                compress_type=zipfile.ZIP_DEFLATED,
            )
            archive.writestr(
                "OEBPS/chapter1.xhtml",
                """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body>
    <h1>Chapter 1</h1>
    <p>Hello from test EPUB content.</p>
  </body>
</html>
""",
                compress_type=zipfile.ZIP_DEFLATED,
            )

        return SimpleUploadedFile(
            "test.epub",
            epub_buffer.getvalue(),
            content_type="application/epub+zip",
        )

    def test_conversion_endpoints_exist(self):
        """Test that all conversion endpoints exist and respond."""
        endpoints = [
            "/api/pdf-to-word/",
            "/api/pdf-to-jpg/",
            "/api/jpg-to-pdf/",
            "/api/word-to-pdf/",
            "/api/epub-to-pdf/",
            "/api/pdf-to-epub/",
            "/api/pdf-to-markdown/",
            "/api/compare-pdf/",
            "/api/epub-to-pdf/async/",
            "/api/pdf-to-epub/async/",
            "/api/pdf-to-markdown/async/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                    f"Endpoint {endpoint} should exist",
                )
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_200_OK,
                        status.HTTP_301_MOVED_PERMANENTLY,
                        status.HTTP_302_FOUND,
                        status.HTTP_403_FORBIDDEN,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                    ],
                )

    def test_pdf_to_word_validation_empty_file(self):
        """Test validation of empty file."""
        from src.api.pdf_convert.pdf_to_word.serializers import PDFToWordSerializer

        empty_file = SimpleUploadedFile(
            "empty.pdf", b"", content_type="application/pdf"
        )
        serializer = PDFToWordSerializer(data={"pdf_file": empty_file})
        self.assertFalse(serializer.is_valid())
        self.assertIn("pdf_file", serializer.errors)

    def test_pdf_to_jpg_validation_dpi_range(self):
        """Test DPI validation for PDF to JPG."""
        from src.api.pdf_convert.pdf_to_jpg.serializers import PDFToJPGSerializer

        pdf_file_low = self._create_test_pdf()
        serializer = PDFToJPGSerializer(data={"pdf_file": pdf_file_low, "dpi": 50})
        self.assertFalse(serializer.is_valid())
        self.assertIn("dpi", serializer.errors)

        pdf_file_high = self._create_test_pdf()
        serializer = PDFToJPGSerializer(data={"pdf_file": pdf_file_high, "dpi": 1000})
        self.assertFalse(serializer.is_valid())
        self.assertIn("dpi", serializer.errors)

    def test_pdf_edit_endpoints_exist(self):
        """Test that all PDF edit endpoints exist and respond."""
        endpoints = [
            "/api/pdf-edit/rotate/",
            "/api/pdf-edit/add-watermark/",
            "/api/pdf-edit/add-page-numbers/",
            "/api/pdf-edit/crop/",
            "/api/pdf-organize/merge/",
            "/api/pdf-organize/split/",
            "/api/pdf-organize/remove-pages/",
            "/api/pdf-organize/extract-pages/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                    f"Endpoint {endpoint} should exist",
                )
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_200_OK,
                        status.HTTP_301_MOVED_PERMANENTLY,
                        status.HTTP_302_FOUND,
                        status.HTTP_403_FORBIDDEN,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                    ],
                )

    def test_split_pdf_creates_zip_with_valid_pdf(self):
        import shutil
        import zipfile

        from PyPDF2 import PdfReader
        from src.api.pdf_organize.split_pdf.utils import split_pdf

        pdf_file = self._create_test_pdf()
        tmp_dir, zip_path = split_pdf(
            pdf_file,
            split_type="page",
            pages="1",
            suffix="_test",
        )
        try:
            self.assertTrue(os.path.exists(zip_path))
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                self.assertEqual(len(names), 1)
                data = zf.read(names[0])
                self.assertTrue(data.startswith(b"%PDF"))

                # Ensure extracted PDF is readable
                with zf.open(names[0]) as f:
                    reader = PdfReader(f)
                    self.assertEqual(len(reader.pages), 1)
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_compress_pdf_levels_affect_output_size(self):
        import shutil

        from PyPDF2 import PdfReader
        from src.api.pdf_organize.compress_pdf.utils import compress_pdf

        pdf_file_low = self._create_test_pdf_with_jpeg()
        input_low, out_low = compress_pdf(
            pdf_file_low, compression_level="low", suffix="_test"
        )
        try:
            pdf_file_high = self._create_test_pdf_with_jpeg()
            input_high, out_high = compress_pdf(
                pdf_file_high, compression_level="high", suffix="_test"
            )
            try:
                self.assertTrue(os.path.exists(out_low))
                self.assertTrue(os.path.exists(out_high))

                # Ensure both PDFs are readable
                PdfReader(out_low)
                PdfReader(out_high)

                size_low = os.path.getsize(out_low)
                size_high = os.path.getsize(out_high)

                # High should be <= low on an image-heavy PDF
                self.assertLessEqual(size_high, size_low)
            finally:
                tmp_dir_high = os.path.dirname(input_high)
                if tmp_dir_high and os.path.isdir(tmp_dir_high):
                    shutil.rmtree(tmp_dir_high, ignore_errors=True)
        finally:
            tmp_dir_low = os.path.dirname(input_low)
            if tmp_dir_low and os.path.isdir(tmp_dir_low):
                shutil.rmtree(tmp_dir_low, ignore_errors=True)

    def test_crop_pdf_fast_path_creates_cropped_pdf(self):
        import shutil

        from PyPDF2 import PdfReader
        from src.api.pdf_edit.crop_pdf.utils import crop_pdf

        pdf_file = self._create_test_pdf()
        input_path, output_path = crop_pdf(
            pdf_file,
            x=0,
            y=0,
            width=100,
            height=150,
            pages="1",
            scale_to_page_size=False,
            suffix="_test",
        )
        try:
            self.assertTrue(os.path.exists(output_path))
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 1)
            page = reader.pages[0]
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            self.assertAlmostEqual(w, 100.0, delta=0.01)
            self.assertAlmostEqual(h, 150.0, delta=0.01)
        finally:
            tmp_dir = os.path.dirname(input_path)
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_merge_pdf_creates_pdf_with_expected_pages(self):
        import shutil

        from PyPDF2 import PdfReader
        from src.api.pdf_organize.merge_pdf.utils import merge_pdf

        pdf1 = self._create_test_pdf()
        pdf2 = self._create_test_pdf()
        tmp_dir, output_path = merge_pdf([pdf1, pdf2], order="upload", suffix="_test")
        try:
            self.assertTrue(os.path.exists(output_path))
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 2)
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_epub_to_pdf_requires_premium_and_succeeds_for_premium_user(self):
        """EPUB to PDF endpoint should enforce premium and convert for active premium users."""
        endpoint = "/api/epub-to-pdf/"

        # Anonymous user
        response = self.client.post(
            endpoint,
            {"epub_file": self._create_test_epub()},
            format="multipart",
            REMOTE_ADDR="127.0.0.1",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated non-premium user
        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="epub-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"epub_file": self._create_test_epub()},
            format="multipart",
            REMOTE_ADDR="127.0.0.2",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Premium user
        premium_user = user_model.objects.create_user(
            email="epub-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        response = self.client.post(
            endpoint,
            {"epub_file": self._create_test_epub()},
            format="multipart",
            REMOTE_ADDR="127.0.0.3",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", response.get("Content-Disposition", ""))

    def test_pdf_to_epub_requires_premium_and_succeeds_for_premium_user(self):
        """PDF to EPUB endpoint should enforce premium and convert for active premium users."""
        endpoint = "/api/pdf-to-epub/"

        # Anonymous user
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.4",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated non-premium user
        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="pdfepub-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.5",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Premium user
        premium_user = user_model.objects.create_user(
            email="pdfepub-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.6",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/epub+zip", response["Content-Type"])
        self.assertIn(".epub", response.get("Content-Disposition", ""))

    def test_epub_to_pdf_async_requires_premium_and_starts_task_for_premium_user(self):
        """Async EPUB to PDF endpoint should enforce premium and return task metadata."""
        endpoint = "/api/epub-to-pdf/async/"

        response = self.client.post(
            endpoint,
            {"epub_file": self._create_test_epub()},
            format="multipart",
            REMOTE_ADDR="127.0.0.7",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="epub-async-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"epub_file": self._create_test_epub()},
            format="multipart",
            REMOTE_ADDR="127.0.0.8",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        premium_user = user_model.objects.create_user(
            email="epub-async-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        with patch(
            "src.api.epub_convert.async_views.generic_conversion_task.apply_async"
        ) as mock_apply_async:
            mock_apply_async.return_value = MagicMock(id="epub-async-task")
            response = self.client.post(
                endpoint,
                {"epub_file": self._create_test_epub()},
                format="multipart",
                REMOTE_ADDR="127.0.0.9",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data.get("task_id"))
        self.assertEqual(response.data.get("status"), "PENDING")

    def test_pdf_to_epub_async_requires_premium_and_starts_task_for_premium_user(self):
        """Async PDF to EPUB endpoint should enforce premium and return task metadata."""
        endpoint = "/api/pdf-to-epub/async/"

        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.10",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="pdfepub-async-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.11",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        premium_user = user_model.objects.create_user(
            email="pdfepub-async-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        with patch(
            "src.api.epub_convert.async_views.generic_conversion_task.apply_async"
        ) as mock_apply_async:
            mock_apply_async.return_value = MagicMock(id="pdfepub-async-task")
            response = self.client.post(
                endpoint,
                {"pdf_file": self._create_test_text_pdf()},
                format="multipart",
                REMOTE_ADDR="127.0.0.12",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data.get("task_id"))
        self.assertEqual(response.data.get("status"), "PENDING")

    def test_pdf_to_markdown_requires_premium_and_succeeds_for_premium_user(self):
        """PDF to Markdown endpoint should enforce premium and convert for premium users."""
        endpoint = "/api/pdf-to-markdown/"

        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.13",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="pdfmd-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.14",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        premium_user = user_model.objects.create_user(
            email="pdfmd-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.15",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/markdown", response["Content-Type"])
        self.assertIn(".md", response.get("Content-Disposition", ""))

    def test_pdf_to_markdown_async_requires_premium_and_starts_task(self):
        """Async PDF to Markdown endpoint should enforce premium and return task metadata."""
        endpoint = "/api/pdf-to-markdown/async/"

        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.16",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="pdfmd-async-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {"pdf_file": self._create_test_text_pdf()},
            format="multipart",
            REMOTE_ADDR="127.0.0.17",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        premium_user = user_model.objects.create_user(
            email="pdfmd-async-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        with patch(
            "src.api.pdf_convert.async_views.generic_conversion_task.apply_async"
        ) as mock_apply_async:
            mock_apply_async.return_value = MagicMock(id="pdfmd-async-task")
            response = self.client.post(
                endpoint,
                {"pdf_file": self._create_test_text_pdf()},
                format="multipart",
                REMOTE_ADDR="127.0.0.18",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data.get("task_id"))
        self.assertEqual(response.data.get("status"), "PENDING")

    def test_compare_pdf_requires_premium_and_returns_zip_for_premium_user(self):
        """Compare PDF endpoint should enforce premium and return ZIP report."""
        endpoint = "/api/compare-pdf/"

        response = self.client.post(
            endpoint,
            {
                "pdf_file_1": self._create_test_text_pdf("Version A"),
                "pdf_file_2": self._create_test_text_pdf("Version B"),
            },
            format="multipart",
            REMOTE_ADDR="127.0.0.19",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user_model = get_user_model()
        free_user = user_model.objects.create_user(
            email="compare-free@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=free_user)
        response = self.client.post(
            endpoint,
            {
                "pdf_file_1": self._create_test_text_pdf("Version A"),
                "pdf_file_2": self._create_test_text_pdf("Version B"),
            },
            format="multipart",
            REMOTE_ADDR="127.0.0.20",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        premium_user = user_model.objects.create_user(
            email="compare-premium@example.com",
            password="pass1234",
            is_premium=True,
        )
        self.client.force_authenticate(user=premium_user)
        response = self.client.post(
            endpoint,
            {
                "pdf_file_1": self._create_test_text_pdf("Version A"),
                "pdf_file_2": self._create_test_text_pdf("Version B"),
                "diff_threshold": 30,
            },
            format="multipart",
            REMOTE_ADDR="127.0.0.21",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/zip", response["Content-Type"])
        self.assertIn(".zip", response.get("Content-Disposition", ""))

        archive_bytes = b"".join(response.streaming_content)
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
        names = set(archive.namelist())
        self.assertIn("report.md", names)
        self.assertIn("report.json", names)
        self.assertTrue(any(name.endswith("_diff.png") for name in names))
