"""Tests for per-tool tutorial video embedding (tool_videos.yaml → page)."""

import json
import re

from django.core.cache import cache
from django.test import Client, TestCase
from src.frontend.tool_videos import TOOL_VIDEOS, _load


def _video_jsonld(html: str) -> dict:
    """Extract and parse the VideoObject JSON-LD from a rendered page."""
    for block in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        if "VideoObject" in block:
            return json.loads(block)  # raises if the template emitted invalid JSON
    raise AssertionError("no VideoObject JSON-LD on page")


class ToolVideoLoaderTests(TestCase):
    """The YAML loader and its defensive gating."""

    def test_known_entries_present_and_shaped(self):
        # A seeded tool and the homepage must load with a video id + upload date.
        for key in ("word_to_pdf", "homepage"):
            self.assertIn(key, TOOL_VIDEOS)
            self.assertTrue(TOOL_VIDEOS[key]["video_id"])
            self.assertTrue(TOOL_VIDEOS[key]["upload_date"])

    def test_tool_without_video_is_absent(self):
        # Gating: a tool with no YAML entry must not resolve to a video.
        self.assertIsNone(TOOL_VIDEOS.get("sign_pdf"))

    def test_malformed_entries_are_dropped(self):
        # One bad edit must not 500 every page: entries missing video_id / not a
        # dict are skipped, valid ones survive. _load reads the real file, so we
        # can only assert it returns a clean dict of well-formed entries.
        loaded = _load()
        self.assertTrue(
            all(isinstance(v, dict) and v.get("video_id") for v in loaded.values())
        )


def _embed(vid: str) -> str:
    """The crawlable player marker: the click-to-play facade button.

    The embed is a facade (thumbnail + play button, iframe injected on click) so
    the YT player stays off the critical path — PSI flagged it on every video
    page. Indexability relies on the VideoObject JSON-LD (embedUrl + thumbnail),
    which is Google's supported path and is asserted alongside this marker.
    """
    return f'data-video-id="{vid}"'


class ToolVideoRenderTests(TestCase):
    """The video facade + VideoObject JSON-LD reach the rendered page."""

    def setUp(self):
        cache.clear()  # anonymous_cache_page can leak pages across tests
        self.client = Client()

    def test_tool_page_with_video_renders_facade_and_jsonld(self):
        resp = self.client.get("/word-to-pdf/", follow=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn(_embed("ozMzrlVOTvQ"), html)
        self.assertIn("i.ytimg.com/vi/ozMzrlVOTvQ/", html)  # facade thumbnail
        self.assertNotIn("<iframe", html)  # player only injected on click
        obj = _video_jsonld(html)
        self.assertEqual(obj["duration"], "PT1M38S")
        self.assertEqual(
            obj["embedUrl"], "https://www.youtube-nocookie.com/embed/ozMzrlVOTvQ"
        )

    def test_bespoke_template_tool_renders_video(self):
        # crop_pdf/add_watermark/jpg_to_pdf have hand-written templates that
        # extend base.html directly (not the generic), so the video must be
        # wired into them too — regression guard for that gap.
        for path, vid in (
            ("/pdf-edit/crop/", "GfvVwZyu-h0"),
            ("/pdf-edit/add-watermark/", "s0OG8dU8G0o"),
            ("/jpg-to-pdf/", "vx_Mrk4DkMw"),
        ):
            resp = self.client.get(path, follow=True)
            self.assertEqual(resp.status_code, 200, path)
            html = resp.content.decode()
            self.assertIn(_embed(vid), html, path)
            self.assertIn("VideoObject", html, path)

    def test_tool_page_without_video_renders_neither(self):
        resp = self.client.get("/pdf-edit/sign/", follow=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn("yt-facade", html)
        self.assertNotIn("VideoObject", html)

    def test_homepage_renders_overview_video(self):
        resp = self.client.get("/", follow=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn(_embed("53XxE5XBP24"), html)
        self.assertIn("See Convertica in action", html)
        obj = _video_jsonld(html)  # asserts valid JSON + presence
        self.assertEqual(obj["duration"], "PT2M26S")
