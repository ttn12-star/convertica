"""Tests for custom i18n views and URL cleanup helpers."""

from django.test import RequestFactory, SimpleTestCase
from src.frontend.i18n_views import remove_all_language_prefixes, set_language


class I18nViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_remove_all_language_prefixes_keeps_query(self):
        self.assertEqual(remove_all_language_prefixes("/es?x=1"), "/?x=1")

    def test_remove_all_language_prefixes_removes_multiple_prefixes(self):
        self.assertEqual(
            remove_all_language_prefixes("/es/es/pdf-edit/crop/"),
            "/pdf-edit/crop/",
        )

    def test_set_language_does_not_create_double_prefix_with_query(self):
        request = self.factory.post(
            "/i18n/setlang/",
            data={"language": "es", "next": "/es?x=1"},
            HTTP_HOST="convertica.net",
        )
        response = set_language(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/es/?x=1")
