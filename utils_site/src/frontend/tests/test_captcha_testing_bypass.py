"""CAPTCHA enforcement must be inert under TESTING (CONVERTICA review).

CaptchaRequirementMiddleware forces session['captcha_required']=True when a
request lacks a first-party Referer and DEBUG is off. Under `manage.py test`
DEBUG is off and the test client sends no Referer, so every premium-tool
endpoint test 400'd with 'CAPTCHA required'. The gates now also skip when
settings.TESTING, which is only true during the test runner (sys.argv[1]=='test'),
so production enforcement is unchanged.
"""

from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase, override_settings
from src.frontend.middleware import CaptchaRequirementMiddleware


class CaptchaTestingBypassTests(SimpleTestCase):
    def _process(self):
        mw = CaptchaRequirementMiddleware(lambda req: _Resp())
        request = RequestFactory().post("/api/pdf-to-markdown/")  # no Referer
        request.session = {}
        mw(request)
        return request.session.get("captcha_required", False)

    @override_settings(DEBUG=False, TESTING=True)
    def test_no_captcha_forced_under_testing(self):
        self.assertFalse(self._process())

    @override_settings(DEBUG=False, TESTING=False)
    def test_captcha_forced_in_production_like_env(self):
        self.assertTrue(self._process())


class _Resp:
    status_code = 200
