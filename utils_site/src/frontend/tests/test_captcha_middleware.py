from django.test import RequestFactory, TestCase, override_settings
from src.frontend.middleware import CaptchaRequirementMiddleware


@override_settings(DEBUG=False)
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
