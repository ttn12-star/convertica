import re

from django.core.cache import cache
from django.test import TestCase
from django.utils import translation


class CompressSizeLandingTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        translation.activate("en")

    def test_landing_per_size_is_indexable_and_preselects_the_target(self):
        for slug, kb in (("100kb", "100"), ("1mb", "1024")):
            response = self.client.get(f"/en/pdf-organize/compress/to-{slug}/")
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertRegex(html, rf'<option value="{kb}" selected>')
            canonical = f'rel="canonical" href="https://testserver/en/pdf-organize/compress/to-{slug}/"'
            self.assertTrue(canonical in html, f"no self-canonical on {slug}")
            hreflang = f'hreflang="ru" href="https://testserver/ru/pdf-organize/compress/to-{slug}/"'
            self.assertTrue(hreflang in html, f"no ru hreflang on {slug}")
            self.assertRegex(html, r'name="robots" content="index')
            title = re.search(r"<title>([^<]*)", html).group(1)
            self.assertIn("Compress PDF to", title)

        self.assertEqual(
            self.client.get("/en/pdf-organize/compress/to-3mb/").status_code, 404
        )
        main = self.client.get("/en/pdf-organize/compress/").content.decode()
        self.assertTrue("/en/pdf-organize/compress/to-200kb/" in main, "no link")
        self.assertRegex(main, r'<option value="" selected>')
        sitemap = self.client.get("/sitemap-en.xml").content.decode()
        self.assertTrue(
            "/en/pdf-organize/compress/to-500kb/" in sitemap, "not in sitemap"
        )
