import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LOCALES = ["ar", "es", "hi", "id", "pl", "ru"]
# Representative sentinel msgids that must be translated in every locale.
SENTINEL = "Install the Convertica app"
# Shared by the breadcrumb label and the footer nav link.
FOOTER_SENTINEL = "Install the App"


def _po_path(lang):
    return Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"


class InstallI18nTests(SimpleTestCase):
    def test_sentinel_translated_in_all_locales(self):
        for lang in LOCALES:
            text = _po_path(lang).read_text(encoding="utf-8")
            # msgid present AND followed by a non-empty msgstr
            m = re.search(r'msgid "%s"\s*\nmsgstr "(.*)"' % re.escape(SENTINEL), text)
            self.assertIsNotNone(m, f"{lang}: msgid missing")
            self.assertNotEqual(m.group(1).strip(), "", f"{lang}: empty msgstr")

    def test_footer_sentinel_translated_in_all_locales(self):
        for lang in LOCALES:
            text = _po_path(lang).read_text(encoding="utf-8")
            m = re.search(
                r'msgid "%s"\s*\nmsgstr "(.*)"' % re.escape(FOOTER_SENTINEL), text
            )
            self.assertIsNotNone(m, f"{lang}: msgid missing")
            self.assertNotEqual(m.group(1).strip(), "", f"{lang}: empty msgstr")

    def test_no_em_dash_in_new_translations(self):
        for lang in LOCALES:
            text = _po_path(lang).read_text(encoding="utf-8")
            tail = text.split("Install the Convertica app")[-1][:8000]
            self.assertNotIn("—", tail, f"{lang}: em-dash in new install strings")
