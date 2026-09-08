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

    def _premium_client(self, tag):
        user = self._user(premium=True, tag=tag)
        self.client.force_authenticate(user=user)
        return user

    def test_boards_roundtrip_and_unknown_preset_tile_dropped(self):
        self._premium_client("bd")
        presets = [
            {
                "id": "p1",
                "name": "Invoices",
                "toolUrl": "/en/pdf-to-pdfa/",
                "toolKey": "pdf_to_pdfa",
            },
        ]
        boards = [
            {
                "id": "b1",
                "name": "Accounting",
                "isDefault": True,
                "createdAt": 1725800000000,
                "tiles": [
                    {"id": "t1", "kind": "preset", "presetId": "p1", "size": "m"},
                    {"id": "t2", "kind": "preset", "presetId": "ghost", "size": "s"},
                    {"id": "t3", "kind": "tasks", "size": "xl"},
                ],
            }
        ]
        response = self.client.put(
            self.ENDPOINT, {"presets": presets, "boards": boards}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        board = response.data["boards"][0]
        self.assertEqual(board["name"], "Accounting")
        self.assertTrue(board["isDefault"])
        tile_ids = [t["id"] for t in board["tiles"]]
        self.assertEqual(tile_ids, ["t1", "t3"])  # ghost preset dropped
        self.assertEqual(board["tiles"][1]["size"], "m")  # bad size → default
        self.assertEqual(response.data["presets"][0]["toolKey"], "pdf_to_pdfa")

        stored = self.client.get(self.ENDPOINT).data
        self.assertEqual(stored["boards"], response.data["boards"])

    def test_unknown_tool_key_is_blanked(self):
        self._premium_client("tk")
        presets = [
            {"id": "p1", "name": "X", "toolUrl": "/en/x/", "toolKey": "not_a_tool"}
        ]
        response = self.client.put(self.ENDPOINT, {"presets": presets}, format="json")
        self.assertEqual(response.data["presets"][0]["toolKey"], "")

    def test_too_many_boards_rejected(self):
        self._premium_client("mb")
        boards = [{"id": f"b{i}", "name": f"B{i}", "tiles": []} for i in range(6)]
        response = self.client.put(
            self.ENDPOINT, {"presets": [], "boards": boards}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tiles_capped_at_twenty(self):
        self._premium_client("tc")
        tiles = [{"id": f"t{i}", "kind": "tasks", "size": "s"} for i in range(25)]
        boards = [{"id": "b1", "name": "Big", "tiles": tiles}]
        response = self.client.put(
            self.ENDPOINT, {"presets": [], "boards": boards}, format="json"
        )
        self.assertEqual(len(response.data["boards"][0]["tiles"]), 20)

    def test_put_without_boards_keeps_stored_boards(self):
        user = self._premium_client("kb")
        UserWorkflowSet.objects.create(
            user=user, presets=[], boards=[{"id": "b1", "name": "Keep", "tiles": []}]
        )
        response = self.client.put(self.ENDPOINT, {"presets": []}, format="json")
        self.assertEqual(response.data["boards"][0]["name"], "Keep")

    def test_preset_tile_with_empty_preset_id_dropped(self):
        self._premium_client("ei")
        presets = [{"name": "No ID", "toolUrl": "/en/x/"}]  # id defaults to ""
        boards = [
            {
                "id": "b1",
                "name": "Board",
                "tiles": [{"id": "t1", "kind": "preset", "size": "s"}],  # no presetId
            }
        ]
        response = self.client.put(
            self.ENDPOINT, {"presets": presets, "boards": boards}, format="json"
        )
        self.assertEqual(response.data["boards"][0]["tiles"], [])
