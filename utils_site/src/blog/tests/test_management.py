"""Tests for the import_blog_articles management command."""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from pathlib import Path

import yaml
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from src.blog.management.commands.import_blog_articles import resolve_publish_date
from src.blog.models import Article, ArticleCategory


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


def _base_payload(slug: str = "demo-article", **overrides) -> dict:
    payload = {
        "slug": slug,
        "status": "published",
        "category_slug": "use-cases",
        "relevant_tool": "compress_pdf",
        "title_en": "Demo Article Title",
        "meta_title_en": "Demo Meta Title",
        "meta_description_en": "Short demo description.",
        "meta_keywords_en": "demo, article, pdf",
        "excerpt_en": "Demo excerpt for the article.",
        "ai_metadata": {
            "topics": ["demo"],
            "summary": "Demo summary",
        },
        "content_en": "<p>Hello world.</p>",
    }
    payload.update(overrides)
    return payload


class ImporterBaseLanguageTests(TestCase):
    """Importer behaviour for the base-language (`en`) corpus."""

    def setUp(self):
        self.tmp = self._tempdir()
        self.source = self.tmp / "blog_articles"

    def _tempdir(self) -> Path:
        import tempfile

        path = Path(tempfile.mkdtemp(prefix="blog_imp_"))
        self.addCleanup(self._rmtree, path)
        return path

    @staticmethod
    def _rmtree(path: Path) -> None:
        import shutil

        shutil.rmtree(path, ignore_errors=True)

    def _run(self, **kwargs) -> str:
        out = StringIO()
        err = StringIO()
        call_command(
            "import_blog_articles",
            source=str(self.source),
            stdout=out,
            stderr=err,
            **kwargs,
        )
        return out.getvalue() + err.getvalue()

    def test_creates_article_and_category(self):
        _write_yaml(self.source / "en" / "demo.yaml", _base_payload())

        self._run()

        self.assertEqual(Article.objects.count(), 1)
        article = Article.objects.get(slug="demo-article")
        self.assertEqual(article.title_en, "Demo Article Title")
        self.assertEqual(article.relevant_tool, "compress_pdf")
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)
        self.assertEqual(article.ai_metadata["summary"], "Demo summary")

        category = article.category
        self.assertIsNotNone(category)
        self.assertEqual(category.slug, "use-cases")
        self.assertEqual(category.name_en, "Use Cases")
        # Localised category names are seeded from the importer dict.
        self.assertIn("ru", category.translations)
        self.assertEqual(category.translations["ru"]["name"], "Сценарии")

    def test_is_idempotent(self):
        _write_yaml(self.source / "en" / "demo.yaml", _base_payload())

        self._run()
        first = Article.objects.get(slug="demo-article")
        first_published_at = first.published_at

        self._run()
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(ArticleCategory.objects.count(), 1)
        # published_at must NOT be reset by a subsequent re-import.
        again = Article.objects.get(slug="demo-article")
        self.assertEqual(again.published_at, first_published_at)

    def test_reimport_without_changes_keeps_updated_at(self):
        """updated_at is the sitemap's <lastmod> — a no-op deploy must not bump it.

        Saving unconditionally made all articles claim "changed today" after
        every deploy, which burned Google's crawl budget on refresh instead of
        the new pages.
        """
        _write_yaml(self.source / "en" / "demo.yaml", _base_payload())
        self._run()
        before = Article.objects.get(slug="demo-article").updated_at

        output = self._run()

        after = Article.objects.get(slug="demo-article").updated_at
        self.assertEqual(after, before)
        self.assertIn("Unchanged (skipped):     1", output)

        # A real content edit must still go through.
        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(content_en="<p>Edited.</p>"),
        )
        self._run()
        edited = Article.objects.get(slug="demo-article")
        self.assertEqual(edited.content_en, "<p>Edited.</p>")
        self.assertGreater(edited.updated_at, before)

    def test_status_override(self):
        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(status="published"),
        )

        self._run(status="draft")

        article = Article.objects.get(slug="demo-article")
        self.assertEqual(article.status, "draft")
        # Override to draft on first import → no published_at set.
        self.assertIsNone(article.published_at)

    def test_dry_run_writes_nothing(self):
        _write_yaml(self.source / "en" / "demo.yaml", _base_payload())

        output = self._run(dry_run=True)

        self.assertIn("[DRY RUN]", output)
        self.assertEqual(Article.objects.count(), 0)
        self.assertEqual(ArticleCategory.objects.count(), 0)

    def test_missing_slug_is_reported_as_error(self):
        bad = _base_payload()
        del bad["slug"]
        _write_yaml(self.source / "en" / "broken.yaml", bad)

        output = self._run()

        self.assertIn("broken.yaml", output)
        self.assertEqual(Article.objects.count(), 0)
        self.assertIn("Errors:                  1", output)

    def test_unknown_source_directory(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_blog_articles",
                source=str(self.source / "does-not-exist"),
                stdout=StringIO(),
            )

    def test_draft_to_published_transition_sets_published_at(self):
        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(status="draft"),
        )
        self._run()
        article = Article.objects.get(slug="demo-article")
        self.assertIsNone(article.published_at)

        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(status="published"),
        )
        self._run()
        article.refresh_from_db()
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)

    def test_future_publish_on_is_held_as_draft_then_goes_live(self):
        """The whole staggered-release mechanism, in one pass.

        A future `publish_on` must hold the row at draft (drafts are what keeps
        it out of the blog list, search, the article page and the sitemap). Once
        the date arrives, the same unchanged YAML must publish it and stamp
        published_at — that flip is what maintenance.publish_scheduled_articles
        relies on, and it is also what fires the per-locale IndexNow ping.
        """
        today = timezone.localdate()

        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(status="published", publish_on=today + timedelta(days=7)),
        )
        output = self._run()
        article = Article.objects.get(slug="demo-article")
        self.assertEqual(article.status, "draft")
        self.assertIsNone(article.published_at)
        self.assertIn("Scheduled (held draft)", output)

        # The date arrives; the YAML itself has not changed.
        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(status="published", publish_on=today),
        )
        self._run()
        article.refresh_from_db()
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)

    def test_unparseable_publish_on_is_an_error(self):
        """A typo'd date must fail loudly, not publish today or never."""
        _write_yaml(
            self.source / "en" / "demo.yaml",
            _base_payload(publish_on="next tuesday"),
        )

        output = self._run()

        self.assertIn("publish_on must be an ISO date", output)
        self.assertEqual(Article.objects.count(), 0)


class ImporterTranslationsTests(TestCase):
    def setUp(self):
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="blog_imp_trans_"))
        self.addCleanup(self._cleanup)
        self.source = self.tmp / "blog_articles"
        _write_yaml(self.source / "en" / "demo.yaml", _base_payload())
        call_command(
            "import_blog_articles",
            source=str(self.source),
            stdout=StringIO(),
        )

    def _cleanup(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_translation_writes_into_translations_json(self):
        _write_yaml(
            self.source / "ru" / "demo.yaml",
            {
                "slug": "demo-article",
                "title_ru": "Заголовок",
                "content_ru": "<p>Привет.</p>",
                "excerpt_ru": "Короткий отрывок.",
                "meta_title_ru": "Мета заголовок",
            },
        )

        out = StringIO()
        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=out,
        )

        article = Article.objects.get(slug="demo-article")
        self.assertIn("ru", article.translations)
        ru = article.translations["ru"]
        self.assertEqual(ru["title"], "Заголовок")
        self.assertEqual(ru["content"], "<p>Привет.</p>")
        self.assertEqual(ru["excerpt"], "Короткий отрывок.")
        # Empty optional fields must NOT be persisted.
        self.assertNotIn("meta_keywords", ru)

    def test_reimporting_same_translation_keeps_updated_at(self):
        payload = {
            "slug": "demo-article",
            "title_ru": "Заголовок",
            "content_ru": "<p>Привет.</p>",
        }
        _write_yaml(self.source / "ru" / "demo.yaml", payload)
        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=StringIO(),
        )
        before = Article.objects.get(slug="demo-article").updated_at

        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=StringIO(),
        )

        self.assertEqual(Article.objects.get(slug="demo-article").updated_at, before)

    def test_translation_for_missing_base_article_is_an_error(self):
        _write_yaml(
            self.source / "ru" / "ghost.yaml",
            {
                "slug": "ghost-article",
                "title_ru": "Несуществующий",
                "content_ru": "<p>x</p>",
            },
        )

        out = StringIO()
        err = StringIO()
        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=out,
            stderr=err,
        )

        article = Article.objects.get(slug="demo-article")
        self.assertNotIn("ru", article.translations or {})
        self.assertIn("ghost.yaml", err.getvalue())

    def test_translation_idempotent_update(self):
        _write_yaml(
            self.source / "ru" / "demo.yaml",
            {
                "slug": "demo-article",
                "title_ru": "Версия 1",
                "content_ru": "<p>v1</p>",
            },
        )
        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=StringIO(),
        )

        _write_yaml(
            self.source / "ru" / "demo.yaml",
            {
                "slug": "demo-article",
                "title_ru": "Версия 2",
                "content_ru": "<p>v2</p>",
            },
        )
        call_command(
            "import_blog_articles",
            source=str(self.source),
            lang="ru",
            stdout=StringIO(),
        )

        article = Article.objects.get(slug="demo-article")
        self.assertEqual(article.translations["ru"]["title"], "Версия 2")


class ImporterRealCorpusTests(TestCase):
    """Smoke test against the real `content/blog_articles/` payload."""

    def test_imports_full_corpus(self):
        # Repository root: utils_site/src/blog/tests/test_management.py → up 4 levels
        repo_root = Path(__file__).resolve().parents[4]
        source = repo_root / "content" / "blog_articles"
        if not source.is_dir():
            self.skipTest(f"No corpus at {source}")
        if not list((source / "en").glob("*.yaml")):
            self.skipTest("No EN YAML files in corpus")

        expected_count = len(list((source / "en").glob("*.yaml")))

        out = StringIO()
        call_command(
            "import_blog_articles",
            source=str(source),
            stdout=out,
        )

        # One Article per EN base YAML — derived so adding articles never
        # silently breaks this smoke test.
        self.assertEqual(Article.objects.count(), expected_count)

        # An article with a future `publish_on` is deliberately held at draft,
        # so read the scheduled slugs off disk rather than asserting that the
        # whole corpus is live.
        today = timezone.localdate()
        scheduled = set()
        for yaml_path in (source / "en").glob("*.yaml"):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            publish_on = (data or {}).get("publish_on")
            if publish_on and resolve_publish_date(publish_on) > today:
                scheduled.add(data["slug"])

        # Every imported article must be wired to a category.
        for article in Article.objects.all():
            self.assertIsNotNone(article.category)
            self.assertTrue(article.title_en)
            self.assertTrue(article.content_en)
            if article.slug in scheduled:
                self.assertEqual(article.status, "draft")
                self.assertIsNone(article.published_at)
            else:
                self.assertEqual(article.status, "published")
                self.assertIsNotNone(article.published_at)
        # Output must be error-free.
        self.assertIn("Errors:                  0", out.getvalue())
