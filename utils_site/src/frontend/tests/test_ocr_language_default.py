import re

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import translation


def _selected(html: str, select_id: str) -> str:
    block = re.search(rf'<select id="{select_id}".*?</select>', html, re.S).group(0)
    return re.search(r'<option value="([^"]+)"[^>]*selected', block).group(1)


class OcrLanguageDefaultTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        # Rendering /pl/, /hi/... leaves that language active in this worker
        # thread; later tests asserting English messages would then fail.
        translation.activate("en")

    def test_ocr_defaults_to_the_page_language(self):
        # "auto" is eng+rus+deu+fra+spa+chi_sim: on /pl/ Polish came back as
        # "Zazote gesla jazn"; Arabic, Hindi, Indonesian were not tried at all.
        for lang, expected in (("en", "auto"), ("pl", "pl"), ("ar", "ar")):
            html = self.client.get(f"/{lang}/image/to-text/").content.decode()
            self.assertEqual(_selected(html, "ocrLanguageSelect"), expected, lang)

        user = get_user_model().objects.create_user(
            email="ocr-premium@example.com", password="x", is_premium=True
        )
        self.client.force_login(user)
        for lang, expected in (("en", "auto"), ("pl", "pol"), ("hi", "hin")):
            html = self.client.get(f"/{lang}/pdf-to-word/").content.decode()
            self.assertEqual(_selected(html, "ocrLanguage"), expected, lang)
