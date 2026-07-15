"""Native-script SEO copy render checks for password-protect-image."""

from django.core.cache import cache
from django.test import Client, TestCase

# lang prefix -> native-script header that must appear in the rendered page
NATIVE_HEADERS = {
    "ru": "Запаролить фото",
    "id": "Kunci Foto dengan Password",
    "ar": "قفل الصور بكلمة مرور",
}


class PasswordProtectImageI18nTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_native_script_header_renders_per_locale(self):
        for lang, header in NATIVE_HEADERS.items():
            with self.subTest(lang=lang):
                response = self.client.get(
                    f"/{lang}/image/password-protect-image/", follow=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(header, response.content.decode("utf-8"))
