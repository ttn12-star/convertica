"""Premium workflow-sync endpoint: gating, roundtrip, sanitization, cap."""

from __future__ import annotations

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from src.users.models import User, UserWorkflowSet


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class WorkflowSyncTests(APITestCase):
    ENDPOINT = "/api/workflows/"

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def _user(self, premium: bool, tag: str = ""):
        return User.objects.create_user(
            username=f"wf{tag}{'p' if premium else 'f'}",
            email=f"wf{tag}{'p' if premium else 'f'}@example.com",
            password="x",
            is_premium=premium,
        )

    def test_anonymous_gets_401(self):
        self.assertEqual(
            self.client.get(self.ENDPOINT).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_free_user_gets_403(self):
        self.client.force_authenticate(user=self._user(premium=False))
        self.assertEqual(
            self.client.get(self.ENDPOINT).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_premium_roundtrip(self):
        user = self._user(premium=True, tag="rt")
        self.client.force_authenticate(user=user)

        presets = [
            {
                "id": "123",
                "name": "Weekly Invoices",
                "toolUrl": "/en/batch-converter/",
                "toolLabel": "Batch Converter",
                "notes": "Batch of 10",
                "params": {"ocr_enabled": True, "ocr_language": "rus"},
                "createdAt": 1784000000000,
            }
        ]
        response = self.client.put(self.ENDPOINT, {"presets": presets}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stored = response.data["presets"]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["name"], "Weekly Invoices")
        self.assertEqual(stored[0]["params"]["ocr_enabled"], True)
        self.assertEqual(stored[0]["params"]["ocr_language"], "rus")

        # Empty set is stored as-is (Clear All must propagate).
        self.client.put(self.ENDPOINT, {"presets": []}, format="json")
        self.assertEqual(self.client.get(self.ENDPOINT).data["presets"], [])

    def test_sanitization_drops_garbage(self):
        user = self._user(premium=True, tag="san")
        self.client.force_authenticate(user=user)
        presets = [
            {"name": "ok", "toolUrl": "/en/pdf-to-word/", "params": {"a": {"x": 1}}},
            {"name": "", "toolUrl": "/en/pdf-to-word/"},  # no name → dropped
            {"name": "x", "toolUrl": "https://evil.example/"},  # not site-relative
            "not-a-dict",
        ]
        response = self.client.put(self.ENDPOINT, {"presets": presets}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stored = response.data["presets"]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["name"], "ok")
        # nested dict param value dropped
        self.assertNotIn("params", stored[0])

    def test_cap_of_40(self):
        user = self._user(premium=True, tag="cap")
        self.client.force_authenticate(user=user)
        presets = [{"name": f"p{i}", "toolUrl": "/en/pdf-to-word/"} for i in range(41)]
        response = self.client.put(self.ENDPOINT, {"presets": presets}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserWorkflowSet.objects.filter(user=user).exists())
