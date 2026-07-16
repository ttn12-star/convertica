from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from src.frontend.middleware import TrafficCountingMiddleware
from src.users.models import PageViewDaily

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


def _html_response(request):
    return HttpResponse("<html></html>", content_type="text/html; charset=utf-8")


class TrafficCountingMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mw = TrafficCountingMiddleware(_html_response)

    def _get(self, path, ua=BROWSER_UA):
        return self.mw(self.factory.get(path, HTTP_USER_AGENT=ua))

    def test_human_html_get_is_counted(self):
        self._get("/en/pdf-to-word/")
        row = PageViewDaily.objects.get(path="/en/pdf-to-word/")
        self.assertEqual(row.views, 1)

    def test_repeat_view_increments_same_row(self):
        self._get("/en/pdf-to-word/")
        self._get("/en/pdf-to-word/")
        self.assertEqual(PageViewDaily.objects.count(), 1)
        self.assertEqual(PageViewDaily.objects.get(path="/en/pdf-to-word/").views, 2)

    def test_bot_user_agent_is_not_counted(self):
        self._get("/en/pdf-to-word/", ua="Googlebot/2.1 (+http://www.google.com/bot)")
        self.assertFalse(PageViewDaily.objects.exists())

    def test_empty_user_agent_is_not_counted(self):
        self._get("/en/pdf-to-word/", ua="")
        self.assertFalse(PageViewDaily.objects.exists())

    def test_skipped_prefixes_are_not_counted(self):
        self._get("/api/pdf-to-word/")
        self._get("/admin/")
        self.assertFalse(PageViewDaily.objects.exists())

    def test_offline_shell_is_not_counted(self):
        # PWA service-worker fallback, not a visited page.
        self._get("/offline.html")
        self.assertFalse(PageViewDaily.objects.exists())

    def test_non_html_response_is_not_counted(self):
        mw = TrafficCountingMiddleware(
            lambda r: HttpResponse(b"{}", content_type="application/json")
        )
        mw(self.factory.get("/en/pdf-to-word/", HTTP_USER_AGENT=BROWSER_UA))
        self.assertFalse(PageViewDaily.objects.exists())

    def test_non_200_is_not_counted(self):
        mw = TrafficCountingMiddleware(
            lambda r: HttpResponse("nope", content_type="text/html", status=404)
        )
        mw(self.factory.get("/en/missing/", HTTP_USER_AGENT=BROWSER_UA))
        self.assertFalse(PageViewDaily.objects.exists())

    def test_blog_article_path_is_counted(self):
        # The blog ask: per-article views come for free via the path counter.
        self._get("/blog/how-to-merge-pdf/")
        self.assertEqual(
            PageViewDaily.objects.get(path="/blog/how-to-merge-pdf/").views, 1
        )


class PageViewDailyAdminTest(TestCase):
    def test_changelist_renders_traffic_summary(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pw"
        )
        PageViewDaily.objects.create(
            date=timezone.now().date(), path="/blog/how-to-merge-pdf/", views=5
        )
        self.client.force_login(admin)
        resp = self.client.get(reverse("admin:users_pageviewdaily_changelist"))
        self.assertEqual(resp.status_code, 200)
        # summary block (template renders) + top-pages row present
        self.assertContains(resp, "Unique visitors")
        self.assertContains(resp, "/blog/how-to-merge-pdf/")
