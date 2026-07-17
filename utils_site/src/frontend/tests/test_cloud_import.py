# utils_site/src/frontend/tests/test_cloud_import.py
from allauth.socialaccount.models import SocialApp
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from src.frontend import context_processors


class CloudImportButtonsTests(TestCase):
    """Drive/Dropbox import buttons are feature-flagged by config keys."""

    def setUp(self):
        # The context processor caches the SocialApp client id per process,
        # and tool pages are cached whole — reset both between tests.
        context_processors._google_oauth_client_id_cache = ""
        cache.clear()

    def _tool_page(self):
        return self.client.get(reverse("frontend:pdf_to_word_page")).content.decode()

    @override_settings(
        GOOGLE_PICKER_API_KEY="test-picker-key",
        GOOGLE_PICKER_APP_ID="123456",
        DROPBOX_APP_KEY="test-dropbox-key",
    )
    def test_buttons_render_when_configured(self):
        SocialApp.objects.create(
            provider="google", name="Google", client_id="test-client-id"
        )
        body = self._tool_page()
        self.assertIn('id="googleDriveImport"', body)
        self.assertIn('id="dropboxImport"', body)
        self.assertIn('data-google-client-id="test-client-id"', body)
        self.assertIn("js/cloud-import", body)

    @override_settings(
        GOOGLE_PICKER_API_KEY="", GOOGLE_PICKER_APP_ID="", DROPBOX_APP_KEY=""
    )
    def test_hidden_without_keys(self):
        body = self._tool_page()
        self.assertNotIn('id="cloudImport"', body)
        self.assertNotIn("js/cloud-import", body)

    @override_settings(
        GOOGLE_PICKER_API_KEY="test-picker-key",
        GOOGLE_PICKER_APP_ID="123456",
        DROPBOX_APP_KEY="test-dropbox-key",
    )
    def test_google_hidden_without_socialapp(self):
        # No SocialApp row -> no OAuth client id -> only Dropbox renders.
        body = self._tool_page()
        self.assertNotIn('id="googleDriveImport"', body)
        self.assertIn('id="dropboxImport"', body)

    def test_po_files_have_translations(self):
        # CI's test job doesn't run compilemessages — assert .po content, not
        # rendered output (see memory: ci_no_compilemessages_i18n_tests).
        msgid = 'msgid "Import from Google Drive"'
        for lang in ("ru", "pl", "hi", "es", "id", "ar"):
            path = f"locale/{lang}/LC_MESSAGES/django.po"
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn(msgid, content, f"{lang}: msgid missing")
            idx = content.index(msgid)
            msgstr_line = content[idx:].split("\n")[1]
            self.assertTrue(
                msgstr_line.startswith('msgstr "') and msgstr_line != 'msgstr ""',
                f"{lang}: empty msgstr",
            )
