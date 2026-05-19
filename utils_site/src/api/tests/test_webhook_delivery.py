from unittest.mock import patch

from django.test import TestCase
from src.api.webhook_delivery import deliver
from src.users.models import User


class WebhookDeliveryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@x.com", password="p")
        self.user.webhook_secret = "x" * 32
        self.user.save()

    @patch("src.api.webhook_delivery.requests.post")
    def test_delivers_with_hmac_signature(self, mock_post):
        mock_post.return_value.status_code = 200
        ok = deliver(
            webhook_url="https://example.com/cb",
            payload={"task_id": "abc"},
            user=self.user,
        )
        self.assertTrue(ok)
        sent_sig = mock_post.call_args.kwargs["headers"]["X-Convertica-Signature"]
        self.assertTrue(sent_sig.startswith("sha256="))

    def test_blocks_private_ip(self):
        ok = deliver(
            webhook_url="http://127.0.0.1:9999/",
            payload={},
            user=self.user,
        )
        self.assertFalse(ok)

    def test_blocks_http_scheme(self):
        ok = deliver(
            webhook_url="http://example.com/",
            payload={},
            user=self.user,
        )
        self.assertFalse(ok)

    def test_blocks_localhost(self):
        ok = deliver(
            webhook_url="https://localhost/",
            payload={},
            user=self.user,
        )
        self.assertFalse(ok)
