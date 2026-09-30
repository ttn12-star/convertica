"""Regressions for CONVERTICA-62/63 and the Polar API version pin (2026-09-30)."""

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from src.api.ocr_utils import SITE_LANGUAGES, get_ocr_language_code
from src.api.task_tokens import create_task_token
from src.payments.polar import PolarClient


class OcrLanguageTests(SimpleTestCase):
    def test_every_ocr_language_has_a_tesseract_pack_in_the_image(self):
        # CONVERTICA-62: the tool offered Polish, the image only had English.
        dockerfile = (Path(settings.BASE_DIR) / "ci" / "Dockerfile").read_text()
        installed = set(re.findall(r"tesseract-ocr-([a-z-]+)", dockerfile))
        for code in SITE_LANGUAGES.values():
            self.assertIn(code.replace("_", "-"), installed, code)

    def test_tesseract_codes_pass_through(self):
        # PDF→Word sends "pol"/"chi_sim"; these used to collapse to "eng".
        self.assertEqual(get_ocr_language_code("pol"), "pol")
        self.assertEqual(get_ocr_language_code("chi_sim"), "chi_sim")
        self.assertEqual(get_ocr_language_code("pl"), "pol")
        self.assertEqual(get_ocr_language_code("xx"), "eng")


class PolarVersionPinTests(SimpleTestCase):
    def test_client_pins_api_version(self):
        client = PolarClient(api_key="k", base_url="https://example.invalid")
        self.assertEqual(client._session.headers["Polar-Version"], "2026-04")


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class DuplicateCancelTests(TestCase):
    @patch("src.api.cancel_task_view.celery_app.control.revoke")
    @patch("src.api.cancel_task_view.AsyncResult")
    def test_second_cancel_does_not_signal_worker_again(self, mock_async, mock_revoke):
        # CONVERTICA-63: beforeunload + pagehide cancel the same task twice.
        mock_async.return_value = MagicMock(state="STARTED")
        body = json.dumps(
            {"task_id": "t-1", "task_token": create_task_token("t-1", None)}
        )
        client = APIClient()
        for _ in range(2):
            resp = client.post(
                "/api/cancel-task/", data=body, content_type="application/json"
            )
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_revoke.call_count, 2)  # one revoke pair, not two
