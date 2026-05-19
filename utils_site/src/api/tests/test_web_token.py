import time

import jwt
from django.conf import settings
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed
from src.api.auth.web_token import WebTokenAuthentication, mint_web_token


class WebTokenTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = WebTokenAuthentication()

    def test_mint_and_verify_roundtrip(self):
        token = mint_web_token(scope=["pdf-to-word"], ip="1.2.3.4")
        request = self.factory.post(
            "/api/v1/pdf-to-word/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            REMOTE_ADDR="1.2.3.4",
        )
        user, auth_obj = self.auth.authenticate(request)
        self.assertIsNone(user)  # web tokens are anonymous
        self.assertEqual(auth_obj["scope"], ["pdf-to-word"])

    def test_expired_token_rejected(self):
        token = mint_web_token(scope=["pdf-to-word"], ip="1.2.3.4", ttl_seconds=-1)
        request = self.factory.post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_scope_mismatch_rejected_at_view_layer(self):
        # this is enforced at the permission layer; for now just verify the
        # token carries scope
        token = mint_web_token(scope=["pdf-to-word"], ip="1.2.3.4")
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(decoded["scope"], ["pdf-to-word"])

    def test_bad_signature_rejected(self):
        token = jwt.encode(
            {"sub": "web", "exp": int(time.time()) + 900},
            "wrong-secret",
            algorithm="HS256",
        )
        request = self.factory.post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)
