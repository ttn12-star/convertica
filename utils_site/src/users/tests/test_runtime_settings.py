from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from src.api import conversion_limits
from src.users.models import RuntimeSetting
from src.users.runtime_settings import refresh_runtime_settings


class RuntimeSettingsTestCase(TestCase):
    def tearDown(self):
        RuntimeSetting.objects.all().delete()
        refresh_runtime_settings()
        super().tearDown()

    def test_rejects_sensitive_setting_key(self):
        runtime_setting = RuntimeSetting(key="SECRET_KEY", value="test-secret")

        with self.assertRaises(ValidationError):
            runtime_setting.full_clean()

    def test_runtime_setting_applies_and_restores_original_value(self):
        original_setting_value = settings.MAX_PDF_PAGES_FREE
        original_limit_value = conversion_limits.MAX_PDF_PAGES

        RuntimeSetting.objects.create(
            key="MAX_PDF_PAGES_FREE",
            value=47,
            is_active=True,
        )
        refresh_runtime_settings()

        self.assertEqual(settings.MAX_PDF_PAGES_FREE, 47)
        self.assertEqual(conversion_limits.MAX_PDF_PAGES, 47)

        RuntimeSetting.objects.update(is_active=False)
        refresh_runtime_settings()

        self.assertEqual(settings.MAX_PDF_PAGES_FREE, original_setting_value)
        self.assertEqual(conversion_limits.MAX_PDF_PAGES, original_limit_value)
