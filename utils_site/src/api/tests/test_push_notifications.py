"""Web-push: subscription API gating + sender task with pruning."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from src.users.models import PushSubscription, User


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class PushSubscribeAPITests(APITestCase):
    ENDPOINT = "/api/push/subscribe/"
    PAYLOAD = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
        "keys": {"p256dh": "pkey", "auth": "akey"},
    }

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def _user(self, premium: bool, tag: str = ""):
        return User.objects.create_user(
            username=f"push{tag}{'p' if premium else 'f'}",
            email=f"push{tag}{'p' if premium else 'f'}@example.com",
            password="x",
            is_premium=premium,
        )

    def test_anonymous_401(self):
        response = self.client.post(self.ENDPOINT, self.PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_free_user_403(self):
        self.client.force_authenticate(user=self._user(premium=False))
        response = self.client.post(self.ENDPOINT, self.PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_premium_subscribe_and_unsubscribe(self):
        user = self._user(premium=True, tag="ok")
        self.client.force_authenticate(user=user)

        response = self.client.post(self.ENDPOINT, self.PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = PushSubscription.objects.get(user=user)
        self.assertEqual(row.p256dh, "pkey")

        # Re-subscribe with the same endpoint updates, not duplicates.
        self.client.post(self.ENDPOINT, self.PAYLOAD, format="json")
        self.assertEqual(PushSubscription.objects.filter(user=user).count(), 1)

        response = self.client.delete(
            self.ENDPOINT, {"endpoint": self.PAYLOAD["endpoint"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PushSubscription.objects.filter(user=user).exists())

    def test_invalid_payload_400(self):
        self.client.force_authenticate(user=self._user(premium=True, tag="bad"))
        response = self.client.post(
            self.ENDPOINT, {"endpoint": "http://insecure/", "keys": {}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    VAPID_PRIVATE_KEY="test-private-key",
    VAPID_CLAIMS={"sub": "mailto:admin@convertica.net"},
)
class SendConversionReadyTests(APITestCase):
    def _user(self):
        return User.objects.create_user(
            username="pushee",
            email="pushee@example.com",
            password="x",
            is_premium=True,
        )

    def test_sends_to_all_and_prunes_dead(self):
        from pywebpush import WebPushException
        from src.tasks.push import send_conversion_ready

        user = self._user()
        alive = PushSubscription.objects.create(
            user=user, endpoint="https://push.example/alive", p256dh="p", auth="a"
        )
        PushSubscription.objects.create(
            user=user, endpoint="https://push.example/dead", p256dh="p", auth="a"
        )

        dead_response = MagicMock(status_code=410)

        def fake_webpush(subscription_info, **kwargs):
            if subscription_info["endpoint"].endswith("/dead"):
                raise WebPushException("gone", response=dead_response)
            return MagicMock()

        with patch("pywebpush.webpush", side_effect=fake_webpush) as mock_push:
            send_conversion_ready.apply(
                kwargs={
                    "user_id": user.id,
                    "task_id": "t-push",
                    "output_filename": "report_convertica.docx",
                    "lang": "ru",
                }
            )

        self.assertEqual(mock_push.call_count, 2)
        endpoints = set(
            PushSubscription.objects.filter(user=user).values_list(
                "endpoint", flat=True
            )
        )
        self.assertEqual(endpoints, {alive.endpoint})
        payload = mock_push.call_args_list[0].kwargs["data"]
        self.assertIn("report_convertica.docx", payload)
        self.assertIn("/ru/premium/background-center/", payload)

    @override_settings(VAPID_PRIVATE_KEY="")
    def test_skips_without_keys(self):
        from src.tasks.push import send_conversion_ready

        user = self._user()
        PushSubscription.objects.create(
            user=user, endpoint="https://push.example/x", p256dh="p", auth="a"
        )
        with patch("pywebpush.webpush") as mock_push:
            send_conversion_ready.apply(
                kwargs={
                    "user_id": user.id,
                    "task_id": "t2",
                    "output_filename": "f.pdf",
                }
            )
        mock_push.assert_not_called()
