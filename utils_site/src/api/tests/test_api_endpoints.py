"""
Integration tests for API endpoints.
"""

import os
import tempfile

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

    def test_conversion_endpoints_exist(self):
        """Test that all conversion endpoints exist and respond."""
        endpoints = [
            "/api/pdf-to-word/",
            "/api/pdf-to-jpg/",
            "/api/jpg-to-pdf/",
            "/api/word-to-pdf/",
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
