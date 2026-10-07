from django.test import RequestFactory, TestCase

from utils_site import urls


class ErrorPageCacheTests(TestCase):
    def test_error_pages_do_not_linger_in_the_edge_cache(self):
        # They were "public, max-age=3600": a 500 during a deploy restart was
        # served to everyone for an hour, and so was a pre-deploy 404.
        response = self.client.get("/en/no-such-page-anywhere/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Cache-Control"], "public, max-age=60, s-maxage=60")

        request = RequestFactory().get("/en/")
        self.assertEqual(urls.handler500(request)["Cache-Control"], "no-store")
        self.assertEqual(urls.handler403(request, None)["Cache-Control"], "no-store")
        self.assertEqual(urls.handler400(request, None)["Cache-Control"], "no-store")
