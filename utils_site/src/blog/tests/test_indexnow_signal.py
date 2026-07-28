"""IndexNow pings on article save: one URL per locale, single-URL mode.

Bing Webmaster Tools flagged "IndexNow is in batch mode" because a nightly task
re-submitted the whole sitemap (~735 URLs) via urlList. That sweep is gone; the
per-article signal has to cover the translated URLs it used to cover, and must
use the single-URL endpoint.
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase, override_settings
from src.blog.models import Article


@override_settings(
    INDEXNOW_ENABLED=True,
    INDEXNOW_KEY="0" * 32,
    DEBUG=False,
    SITE_BASE_URL="https://convertica.net",
)
class IndexNowSignalTests(TestCase):
    def _save_and_capture(self, **article_kwargs) -> list[str]:
        # The signal skips test runs at the indexnow.py layer, so patch the
        # submit function itself and assert on the URLs it was handed.
        with mock.patch(
            "src.frontend.indexnow.submit_url_to_indexnow", return_value=True
        ) as submit, mock.patch("src.blog.signals.os.environ", {}), mock.patch(
            "src.blog.signals.sys.argv", ["manage.py"]
        ):
            Article.objects.create(
                slug="indexnow-demo",
                title_en="IndexNow demo",
                content_en="<p>x</p>",
                status="published",
                **article_kwargs,
            )
        return [call.args[0] for call in submit.call_args_list]

    def test_pings_every_locale_the_article_exists_in(self):
        urls = self._save_and_capture(
            translations={
                "ru": {"title": "RU", "content": "<p>ru</p>"},
                "pl": {"title": "PL", "content": "<p>pl</p>"},
            }
        )

        self.assertEqual(
            sorted(urls),
            sorted(
                [
                    "https://convertica.net/en/blog/indexnow-demo/",
                    "https://convertica.net/ru/blog/indexnow-demo/",
                    "https://convertica.net/pl/blog/indexnow-demo/",
                ]
            ),
        )

    def test_untranslated_article_pings_base_locale_only(self):
        self.assertEqual(
            self._save_and_capture(),
            ["https://convertica.net/en/blog/indexnow-demo/"],
        )

    def test_single_url_submit_uses_get_not_batch_post(self):
        from src.frontend.indexnow import submit_url_to_indexnow

        with mock.patch("src.frontend.indexnow.requests.get") as get, mock.patch(
            "src.frontend.indexnow.requests.post"
        ) as post, mock.patch(
            "src.frontend.indexnow.sys.argv", ["manage.py"]
        ), mock.patch(
            "src.frontend.indexnow.os.environ", {}
        ):
            get.return_value = mock.Mock(status_code=200)
            ok = submit_url_to_indexnow("https://convertica.net/en/blog/x/")

        self.assertTrue(ok)
        post.assert_not_called()
        self.assertEqual(get.call_args.args[0], "https://api.indexnow.org/indexnow")
        self.assertEqual(
            get.call_args.kwargs["params"]["url"], "https://convertica.net/en/blog/x/"
        )
