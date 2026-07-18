"""seo_title/seo_meta must not leave a dangling connector/preposition after a
length cut (regression for RU '...архивный PDF по' and EN meta 'Fast &' / 'No')."""

from django.test import SimpleTestCase
from src.frontend.templatetags.seo_extras import seo_meta, seo_title


class SeoTitleTests(SimpleTestCase):
    def test_short_title_unchanged(self):
        t = "PDF to Word | Convertica"
        self.assertEqual(seo_title(t), t)

    def test_ru_dangling_preposition_dropped_and_brand_kept(self):
        # 60-char budget forces a cut; must not end on the preposition "по".
        t = "Конвертер PDF в PDF/A — архивный формат PDF по стандарту | Convertica"
        out = seo_title(t)
        body = out.rsplit("|", 1)[0].strip()
        self.assertFalse(body.endswith("по"), out)
        self.assertTrue(out.endswith("| Convertica"), out)
        self.assertLessEqual(len(out), 65)

    def test_en_dangling_connector_dropped(self):
        t = "Merge PDF files online free and fast and secure and easy | Convertica"
        out = seo_title(t)
        body = out.rsplit("|", 1)[0].strip()
        self.assertFalse(body.endswith(" and"), out)
        self.assertFalse(body.lower().split()[-1] == "and", out)


class SeoMetaTests(SimpleTestCase):
    def test_short_meta_unchanged(self):
        m = "Convert your files fast."
        self.assertEqual(seo_meta(m), m)

    def test_dangling_connector_dropped(self):
        # >155 chars, with a connector sitting right at the word-boundary cut.
        m = ("filler " * 25) + "and tail words that overflow the limit here"
        self.assertGreater(len(m), 155)
        out = seo_meta(m)
        self.assertLessEqual(len(out), 155)
        self.assertNotEqual(out.rstrip().lower().split()[-1], "and", out)
