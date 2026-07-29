"""Every public frontend page must have a sitemap entry.

/image/password-protect-image/ shipped without one and stayed out of the
sitemaps for weeks (Ahrefs "Indexable page not in sitemap", 7 locales, 114
inlinks each) — nothing failed, because the sitemap page list is hand-written
next to, but separately from, the URL conf. This test diffs the two.
"""

from __future__ import annotations

from django.test import TestCase
from django.views.generic import RedirectView
from src.frontend.urls import urlpatterns
from src.frontend.views import _get_sitemap_pages

# Pages deliberately kept out of the sitemaps.
SITEMAP_EXEMPT = {
    # Premium-gated dashboards: they 302 anonymous crawlers. Their public
    # explainer landings (background-tasks/, saved-workflows/) are indexed.
    "premium/workflows/",
    "premium/background-center/",
}


def _public_page_paths() -> set[str]:
    """Literal paths of frontend pages that serve indexable HTML."""
    paths = set()
    for pattern in urlpatterns:
        route = str(pattern.pattern)
        if "<" in route:  # parameterised, not a standalone landing
            continue
        if getattr(pattern.callback, "view_class", None) is RedirectView:
            continue
        paths.add(route)
    return paths


class SitemapCoverageTests(TestCase):
    def test_every_public_page_is_in_the_sitemap(self):
        listed = {page["url"] for page in _get_sitemap_pages()}
        missing = _public_page_paths() - listed - SITEMAP_EXEMPT
        self.assertEqual(
            missing,
            set(),
            "Public page(s) missing from _get_sitemap_pages(): "
            f"{sorted(missing)}. Add them there (and bump the sitemap cache "
            "key), or add them to SITEMAP_EXEMPT with a reason.",
        )
