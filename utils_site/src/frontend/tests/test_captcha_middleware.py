from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from src.frontend.middleware import CaptchaRequirementMiddleware


# TESTING=False so these production-gate assertions aren't short-circuited by
# the test-runner CAPTCHA bypass (the gate is inert under settings.TESTING).
@override_settings(DEBUG=False, TESTING=False)
class CaptchaOriginGateTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CaptchaRequirementMiddleware(
            lambda r: type("R", (), {"status_code": 200})()
        )

    def test_api_post_without_referer_demands_captcha(self):
        request = self.factory.post("/api/jpg-to-pdf/")
        request.session = {}
        self.middleware(request)
        self.assertTrue(request.session.get("captcha_required"))

    def test_authenticated_session_skips_origin_gate(self):
        # A logged-in session (has _auth_user_id) is not a curl script — the
        # no-Referer origin gate must not fire for it, even with no Referer.
        request = self.factory.post("/api/jpg-to-pdf/")
        request.session = {"_auth_user_id": "42"}
        self.middleware(request)
        self.assertFalse(request.session.get("captcha_required"))

    def test_api_post_with_convertica_referer_does_not_demand_captcha(self):
        request = self.factory.post(
            "/api/jpg-to-pdf/", HTTP_REFERER="https://convertica.net/en/jpg-to-pdf/"
        )
        request.session = {}
        self.middleware(request)
        self.assertFalse(request.session.get("captcha_required"))

    def test_api_post_with_foreign_referer_demands_captcha(self):
        request = self.factory.post(
            "/api/jpg-to-pdf/", HTTP_REFERER="https://evil.example.com/"
        )
        request.session = {}
        self.middleware(request)
        self.assertTrue(request.session.get("captcha_required"))

    def test_api_post_with_convertica_origin_only_does_not_demand_captcha(self):
        request = self.factory.post(
            "/api/jpg-to-pdf/",
            HTTP_ORIGIN="https://convertica.net",
        )
        request.session = {}
        self.middleware(request)
        self.assertFalse(request.session.get("captcha_required"))

    def test_api_post_with_subdomain_spoof_demands_captcha(self):
        # Regression: startswith("https://convertica.net") matched
        # https://convertica.net.evil.com/ before the boundary fix.
        request = self.factory.post(
            "/api/jpg-to-pdf/",
            HTTP_REFERER="https://convertica.net.evil.com/foo",
        )
        request.session = {}
        self.middleware(request)
        self.assertTrue(request.session.get("captcha_required"))


# Threshold lowered to 3 so the loops stay short and explicit.
@override_settings(DEBUG=False, TESTING=False, CAPTCHA_AFTER_FAILED_ATTEMPTS=3)
class CaptchaFailedAttemptCountingTest(TestCase):
    """The gate must count abuse (429 / spam 400), not ordinary input errors."""

    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()  # IP-based counter lives in the cache; isolate each test.

    def _mw(self, status_code, headers=None):
        def get_response(_request):
            resp = HttpResponse(status=status_code)
            for k, v in (headers or {}).items():
                resp[k] = v
            return resp

        return CaptchaRequirementMiddleware(get_response)

    def _first_party_request(self):
        # First-party Referer so the origin gate doesn't pre-set captcha_required;
        # we're isolating the failed-attempt counter here.
        request = self.factory.post(
            "/api/text-to-pdf/", HTTP_REFERER="https://convertica.net/en/text-to-pdf/"
        )
        request.session = {}
        return request

    def test_input_validation_400_never_gates(self):
        # A user pasting too-long text (400 + X-Input-Error) is not an attacker —
        # even far past the threshold, no CAPTCHA is demanded. This is the exact
        # bug from the incident.
        mw = self._mw(400, {"X-Input-Error": "1"})
        session = {}
        for _ in range(10):
            request = self.factory.post(
                "/api/text-to-pdf/",
                HTTP_REFERER="https://convertica.net/en/text-to-pdf/",
            )
            request.session = session
            mw(request)
        self.assertFalse(session.get("captcha_required"))
        self.assertNotIn("failed_attempts", session)

    def test_spam_400_gates_at_threshold(self):
        # A honeypot/spam rejection (400 + X-Abuse-Signal) DOES count.
        mw = self._mw(400, {"X-Abuse-Signal": "1"})
        session = {}
        for _ in range(3):
            request = self.factory.post(
                "/api/text-to-pdf/",
                HTTP_REFERER="https://convertica.net/en/text-to-pdf/",
            )
            request.session = session
            mw(request)
        self.assertTrue(session.get("captcha_required"))

    def test_429_gates_at_threshold(self):
        # Rate-limit responses are the primary flood signal and always count.
        mw = self._mw(429)
        session = {}
        for _ in range(3):
            request = self.factory.post(
                "/api/text-to-pdf/",
                HTTP_REFERER="https://convertica.net/en/text-to-pdf/",
            )
            request.session = session
            mw(request)
        self.assertTrue(session.get("captcha_required"))

    def test_success_resets_counter(self):
        # A genuine success clears accumulated failures (recovery path).
        session = {}
        abuse = self._mw(429)
        for _ in range(2):
            request = self._first_party_request()
            request.session = session
            abuse(request)
        self.assertEqual(session.get("failed_attempts"), 2)
        ok = self._mw(200)
        request = self._first_party_request()
        request.session = session
        ok(request)
        self.assertNotIn("failed_attempts", session)


@override_settings(DEBUG=True)
class CaptchaDebugBypassTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CaptchaRequirementMiddleware(
            lambda r: type("R", (), {"status_code": 200})()
        )

    def test_debug_bypasses_origin_gate(self):
        request = self.factory.post("/api/jpg-to-pdf/")  # no Referer
        request.session = {}
        self.middleware(request)
        self.assertFalse(request.session.get("captcha_required"))
