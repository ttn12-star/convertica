"""Replace blog content links to category-root URLs with concrete tool URLs.

Old blog posts (some authored before category indexes were added) link to
`/pdf-edit/`, `/pdf-organize/`, `/image/`, `/pdf-security/`, and the
language-prefixed equivalents. Those parents now 301-redirect to /all-tools/,
which surfaces in Ahrefs as ~14 "3XX redirect" warnings on every full crawl.

This command rewrites those hrefs in-place — directly inside `content_en` and
each entry in the `translations` JSON. Idempotent: running it twice is safe.

Run on prod with:
    python manage.py fix_blog_internal_links            # dry run, prints diff
    python manage.py fix_blog_internal_links --apply    # actually save
"""

import re

from django.core.management.base import BaseCommand
from src.blog.models import Article

# Category roots → most-relevant concrete tool. We pick the most representative
# tool from each category (highest-traffic / canonical action) so anchors keep
# their intent ("rotate PDF pages" link should land on rotate, not the index).
# When a sentence isn't tool-specific, /all-tools/ is the safe fallback.
LANG_PREFIX = r"/(?:[a-z]{2}/)?"
PATTERNS = [
    # Most-specific replacements first (so they don't mask shorter ones)
    (
        rf'(href=")({LANG_PREFIX})pdf-edit/?(")',
        r"\1\2pdf-edit/rotate/\3",
    ),
    (
        rf'(href=")({LANG_PREFIX})pdf-organize/?(")',
        r"\1\2pdf-organize/merge/\3",
    ),
    (
        rf'(href=")({LANG_PREFIX})pdf-security/?(")',
        r"\1\2pdf-security/protect/\3",
    ),
    (
        rf'(href=")({LANG_PREFIX})image/?(")',
        r"\1\2image/optimize/\3",
    ),
]


def rewrite(text: str) -> tuple[str, int]:
    """Apply all patterns. Return (new_text, number_of_replacements)."""
    if not text:
        return text, 0
    total = 0
    for pat, repl in PATTERNS:
        text, n = re.subn(pat, repl, text)
        total += n
    return text, total


class Command(BaseCommand):
    help = "Rewrite blog content links from /pdf-edit/ etc. (which 301-redirect) to concrete tool URLs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Save changes. Without this flag, the command runs in dry-run mode.",
        )

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        articles = Article.objects.all()
        total_articles_changed = 0
        total_replacements = 0

        for article in articles:
            article_replacements = 0
            changed = False

            new_content_en, n = rewrite(article.content_en)
            if n:
                article_replacements += n
                if apply_changes:
                    article.content_en = new_content_en
                changed = True

            translations = dict(article.translations or {})
            for lang_code, entry in list(translations.items()):
                if not isinstance(entry, dict):
                    continue
                old = entry.get("content", "")
                new, n = rewrite(old)
                if n:
                    article_replacements += n
                    if apply_changes:
                        entry["content"] = new
                        translations[lang_code] = entry
                    changed = True

            if changed:
                total_articles_changed += 1
                total_replacements += article_replacements
                self.stdout.write(f"  {article.slug}: {article_replacements} link(s)")
                if apply_changes:
                    article.translations = translations
                    article.save(update_fields=["content_en", "translations"])

        verb = "Updated" if apply_changes else "Would update"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {total_articles_changed} article(s), "
                f"{total_replacements} link replacement(s) total."
            )
        )
        if not apply_changes:
            self.stdout.write(
                self.style.WARNING("Dry run. Re-run with --apply to save changes.")
            )
