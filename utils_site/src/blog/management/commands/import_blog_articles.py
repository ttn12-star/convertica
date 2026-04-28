"""Import blog articles from YAML files into Article / ArticleCategory.

Layout expected on disk:

    content/blog_articles/
        en/
            my-slug.yaml          # base-language source (creates Article)
        ru/
            my-slug.yaml          # translation (writes into Article.translations["ru"])
        ...

Base YAML fields (`en`):

    slug, status, category_slug, relevant_tool,
    title_en, meta_title_en, meta_description_en, meta_keywords_en,
    excerpt_en, ai_metadata (dict), content_en (HTML).

Translation YAML fields (`<lang>` other than `en`):

    slug, title_<lang>, content_<lang>,
    excerpt_<lang>, meta_title_<lang>, meta_description_<lang>, meta_keywords_<lang>.

The command is idempotent — re-running updates existing rows in place.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from src.blog.models import Article, ArticleCategory

CATEGORY_NAMES = {
    "use-cases": {
        "en": "Use Cases",
        "ru": "Сценарии",
        "pl": "Przypadki użycia",
        "hi": "उपयोग के मामले",
        "es": "Casos de uso",
        "id": "Studi kasus",
        "ar": "حالات الاستخدام",
    },
    "how-to-guides": {
        "en": "How-To Guides",
        "ru": "Инструкции",
        "pl": "Poradniki",
        "hi": "कैसे करें गाइड",
        "es": "Guías paso a paso",
        "id": "Panduan langkah demi langkah",
        "ar": "أدلة إرشادية",
    },
    "best-practices": {
        "en": "Best Practices",
        "ru": "Лучшие практики",
        "pl": "Dobre praktyki",
        "hi": "सर्वोत्तम प्रथाएँ",
        "es": "Buenas prácticas",
        "id": "Praktik terbaik",
        "ar": "أفضل الممارسات",
    },
    "comparisons": {
        "en": "Comparisons",
        "ru": "Сравнения",
        "pl": "Porównania",
        "hi": "तुलनाएँ",
        "es": "Comparaciones",
        "id": "Perbandingan",
        "ar": "مقارنات",
    },
}

BASE_LANG = "en"

MAX_TITLE = 200
MAX_META_DESCRIPTION = 500
MAX_EXCERPT = 500
MAX_META_KEYWORDS = 500


class Command(BaseCommand):
    help = "Import blog articles from YAML files in content/blog_articles/<lang>/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="content/blog_articles",
            help="Directory with <lang>/*.yaml subdirectories.",
        )
        parser.add_argument(
            "--lang",
            default=None,
            help="Process only one language (default: every <lang> subdirectory).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without committing to the database.",
        )
        parser.add_argument(
            "--status",
            default=None,
            choices=["draft", "published", "archived"],
            help="Override the status field in every base-language YAML.",
        )

    def handle(self, *args, **opts):
        source = Path(opts["source"]).resolve()
        if not source.is_dir():
            raise CommandError(f"Source directory not found: {source}")

        only_lang = opts["lang"]
        dry_run = opts["dry_run"]
        status_override = opts["status"]

        if only_lang:
            lang_dirs = [source / only_lang]
            if not lang_dirs[0].is_dir():
                raise CommandError(f"Language directory not found: {lang_dirs[0]}")
        else:
            lang_dirs = sorted(p for p in source.iterdir() if p.is_dir())
            if not lang_dirs:
                raise CommandError(f"No <lang> subdirectories under {source}")

        # Always import the base language first so translations can attach.
        lang_dirs = sorted(lang_dirs, key=lambda p: 0 if p.name == BASE_LANG else 1)

        totals = {
            "created": 0,
            "updated": 0,
            "translation_created": 0,
            "translation_updated": 0,
            "errors": 0,
        }

        for lang_dir in lang_dirs:
            lang_code = lang_dir.name
            yaml_files = sorted(lang_dir.glob("*.yaml"))
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\n{lang_code} → {len(yaml_files)} file(s)")
            )
            for yaml_path in yaml_files:
                try:
                    with transaction.atomic():
                        result = self._import_one(yaml_path, lang_code, status_override)
                        if dry_run:
                            transaction.set_rollback(True)
                    totals[result] += 1
                    self.stdout.write(f"  {self._symbol(result)} {yaml_path.name}")
                except Exception as exc:  # noqa: BLE001 — we want to keep going
                    totals["errors"] += 1
                    self.stderr.write(self.style.ERROR(f"  ! {yaml_path.name}: {exc}"))

        self._print_summary(totals, dry_run)

    def _import_one(self, yaml_path: Path, lang_code: str, status_override):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("YAML must be a mapping at the top level")

        slug = data.get("slug")
        if not slug:
            raise ValueError("Missing required field 'slug'")

        if lang_code == BASE_LANG:
            return self._import_base(data, slug, status_override)
        return self._import_translation(data, slug, lang_code)

    def _import_base(self, data: dict, slug: str, status_override) -> str:
        title = (data.get("title_en") or "").strip()
        content = data.get("content_en")
        if not title or not content:
            raise ValueError("Base-language YAML requires 'title_en' and 'content_en'")
        if len(title) > MAX_TITLE:
            raise ValueError(f"title_en is {len(title)} chars, max is {MAX_TITLE}")

        category = self._ensure_category(data.get("category_slug"))
        status = status_override or data.get("status") or "draft"
        relevant_tool = data.get("relevant_tool") or None

        defaults = {
            "title_en": title,
            "content_en": content,
            "excerpt_en": (data.get("excerpt_en") or "")[:MAX_EXCERPT],
            "meta_title_en": (data.get("meta_title_en") or "")[:MAX_TITLE],
            "meta_description_en": (data.get("meta_description_en") or "")[
                :MAX_META_DESCRIPTION
            ],
            "meta_keywords_en": (data.get("meta_keywords_en") or "")[
                :MAX_META_KEYWORDS
            ],
            "ai_metadata": data.get("ai_metadata") or {},
            "relevant_tool": relevant_tool,
            "category": category,
            "status": status,
        }

        article = Article.objects.filter(slug=slug).first()
        if article is None:
            published_at = timezone.now() if status == "published" else None
            Article.objects.create(slug=slug, published_at=published_at, **defaults)
            return "created"

        for key, value in defaults.items():
            setattr(article, key, value)
        # Set published_at on first transition into "published"; preserve the
        # original publication date on subsequent re-imports.
        if status == "published" and not article.published_at:
            article.published_at = timezone.now()
        article.save()
        return "updated"

    def _import_translation(self, data: dict, slug: str, lang_code: str) -> str:
        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist as exc:
            raise ValueError(
                f"Base article '{slug}' not found — import {BASE_LANG}/ first"
            ) from exc

        title_key = f"title_{lang_code}"
        content_key = f"content_{lang_code}"
        if not data.get(title_key) or not data.get(content_key):
            raise ValueError(
                f"Translation YAML must include '{title_key}' and '{content_key}'"
            )

        new_trans = {
            "title": data[title_key],
            "content": data[content_key],
            "excerpt": (data.get(f"excerpt_{lang_code}") or "")[:MAX_EXCERPT],
            "meta_title": (data.get(f"meta_title_{lang_code}") or "")[:MAX_TITLE],
            "meta_description": (data.get(f"meta_description_{lang_code}") or "")[
                :MAX_META_DESCRIPTION
            ],
            "meta_keywords": (data.get(f"meta_keywords_{lang_code}") or "")[
                :MAX_META_KEYWORDS
            ],
        }
        new_trans = {k: v for k, v in new_trans.items() if v}

        translations = dict(article.translations or {})
        existed = lang_code in translations
        translations[lang_code] = new_trans
        article.translations = translations
        article.save(update_fields=["translations", "updated_at"])
        return "translation_updated" if existed else "translation_created"

    def _ensure_category(self, category_slug):
        if not category_slug:
            return None
        names = CATEGORY_NAMES.get(category_slug)
        name_en = names["en"] if names else category_slug.replace("-", " ").title()
        translations = (
            {lang: {"name": n} for lang, n in names.items() if lang != BASE_LANG}
            if names
            else {}
        )
        category, created = ArticleCategory.objects.get_or_create(
            slug=category_slug,
            defaults={"name_en": name_en, "translations": translations},
        )
        if not created and translations and category.translations != translations:
            category.translations = translations
            category.save(update_fields=["translations", "updated_at"])
        return category

    @staticmethod
    def _symbol(result: str) -> str:
        return {
            "created": "+",
            "updated": "~",
            "translation_created": "T+",
            "translation_updated": "T~",
        }.get(result, "?")

    def _print_summary(self, totals: dict, dry_run: bool):
        prefix = "[DRY RUN] " if dry_run else ""
        msg = (
            f"\n{prefix}Summary:\n"
            f"  Articles created:        {totals['created']}\n"
            f"  Articles updated:        {totals['updated']}\n"
            f"  Translations created:    {totals['translation_created']}\n"
            f"  Translations updated:    {totals['translation_updated']}\n"
            f"  Errors:                  {totals['errors']}\n"
        )
        style = self.style.WARNING if totals["errors"] else self.style.SUCCESS
        self.stdout.write(style(msg))
