"""Token gate for WS progress channels + opt-in web-token scope enforcement.

WS progress channels broadcast download_url/filename, so a bare task_id must not
be enough to subscribe (_ws_token_ok). And IsAuthenticatedOrWebToken enforces a
view's declared web_token_scope against the token's scope list when present.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from src.api.auth.permissions import IsAuthenticatedOrWebToken
from src.api.task_tokens import create_task_token
from src.api.ws_auth import ws_token_ok as _ws_token_ok


class WsTokenGateTests(SimpleTestCase):
    def _scope(self, query_string: bytes):
        return {"query_string": query_string, "user": None}

    def test_valid_token_accepted(self):
        tok = create_task_token("task-abc", user_id=None)
        scope = self._scope(f"task_token={tok}".encode())
        self.assertTrue(_ws_token_ok(scope, "task-abc"))

    def test_absent_token_rejected(self):
        self.assertFalse(_ws_token_ok(self._scope(b""), "task-abc"))

    def test_token_for_other_task_rejected(self):
        tok = create_task_token("task-OTHER", user_id=None)
        scope = self._scope(f"task_token={tok}".encode())
        self.assertFalse(_ws_token_ok(scope, "task-abc"))


class _View:
    def __init__(self, slug=None):
        if slug is not None:
            self.web_token_scope = slug


class WebTokenScopeTests(SimpleTestCase):
    def setUp(self):
        self.perm = IsAuthenticatedOrWebToken()

    class _Req:
        def __init__(self, auth):
            self.user = None
            self.auth = auth

    def test_no_declared_scope_passes(self):
        req = self._Req({"sub": "web", "scope": ["pdf-to-word"]})
        self.assertTrue(self.perm.has_permission(req, _View()))

    def test_matching_scope_passes(self):
        req = self._Req({"sub": "web", "scope": ["pdf-to-word"]})
        self.assertTrue(self.perm.has_permission(req, _View("pdf-to-word")))

    def test_wildcard_scope_passes(self):
        req = self._Req({"sub": "web", "scope": ["*"]})
        self.assertTrue(self.perm.has_permission(req, _View("pdf-to-excel")))

    def test_mismatched_scope_rejected(self):
        req = self._Req({"sub": "web", "scope": ["pdf-to-word"]})
        self.assertFalse(self.perm.has_permission(req, _View("pdf-to-excel")))

    def test_non_web_auth_rejected(self):
        req = self._Req(None)
        self.assertFalse(self.perm.has_permission(req, _View()))
