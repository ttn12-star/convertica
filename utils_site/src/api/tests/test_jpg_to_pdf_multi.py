"""Multi-file JPG→PDF endpoint behaviour.

The multi-file branch of JPGToPDFAPIView.post() reads request.FILES
directly instead of going through post_async, so it must apply the same
per-file validation the single-file path gets from the base class, and
must stream the merged PDF instead of buffering it in the gunicorn
worker (the web container shares a tight memory cgroup).
"""

from __future__ import annotations

import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from src.api import conversion_limits


def _jpeg_upload(name="photo.jpg", size=(40, 40), colour=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _noisy_jpeg_upload(name="big.jpg", size=(256, 256)):
    """A JPEG that compresses poorly, so its byte size stays large."""
    raw = os.urandom(size[0] * size[1] * 3)
    img = Image.frombytes("RGB", size, raw)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class JpgToPdfMultiFileTests(TestCase):
    URL = "/api/jpg-to-pdf/"

    def test_merged_pdf_is_streamed_and_valid(self):
        response = self.client.post(
            self.URL,
            {"image_file": [_jpeg_upload("a.jpg"), _jpeg_upload("b.jpg")]},
        )
        self.assertEqual(response.status_code, 200)
        # FileResponse streams from disk; a buffered HttpResponse would hold
        # the whole merged PDF in worker memory.
        self.assertTrue(response.streaming)
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertIn("merged_convertica.pdf", response["Content-Disposition"])

    def test_multi_file_upload_enforces_file_count_limit(self):
        """The multi branch runs a synchronous render loop per image — an
        unbounded file count lets one request hog a gunicorn worker."""
        from src.api.pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView

        too_many = JPGToPDFAPIView.MAX_MULTI_IMAGE_FILES + 1
        files = [_jpeg_upload(f"img_{i}.jpg") for i in range(too_many)]
        response = self.client.post(self.URL, {"image_file": files})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_multi_file_upload_enforces_per_file_size_limit(self):
        small = _jpeg_upload("small.jpg")
        big = _noisy_jpeg_upload("big.jpg")
        self.assertGreater(big.size, 5_000)

        with override_settings(
            MAX_FILE_SIZE_FREE=5_000, MAX_FILE_SIZE_HEAVY_FREE=5_000
        ):
            conversion_limits.reload_from_settings()
            try:
                response = self.client.post(self.URL, {"image_file": [small, big]})
            finally:
                pass
        conversion_limits.reload_from_settings()

        self.assertEqual(response.status_code, 413)
