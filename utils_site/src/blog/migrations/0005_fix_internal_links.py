"""Data migration: rewrite blog content links from /pdf-edit/ etc. to concrete tools.

Mirrors the standalone `fix_blog_internal_links` management command but runs
automatically during `migrate` on the next deploy. Idempotent — safe even if
the command was already run by hand.
"""

import re

from django.db import migrations

LANG_PREFIX = r"/(?:[a-z]{2}/)?"
PATTERNS = [
    (rf'(href=")({LANG_PREFIX})pdf-edit/?(")', r"\1\2pdf-edit/rotate/\3"),
    (rf'(href=")({LANG_PREFIX})pdf-organize/?(")', r"\1\2pdf-organize/merge/\3"),
    (rf'(href=")({LANG_PREFIX})pdf-security/?(")', r"\1\2pdf-security/protect/\3"),
    (rf'(href=")({LANG_PREFIX})image/?(")', r"\1\2image/optimize/\3"),
]


def _rewrite(text):
    if not text:
        return text, 0
    total = 0
    for pat, repl in PATTERNS:
        text, n = re.subn(pat, repl, text)
        total += n
    return text, total


def fix_links(apps, schema_editor):
    Article = apps.get_model("blog", "Article")
    for article in Article.objects.all().iterator():
        changed = False
        new_content_en, n = _rewrite(article.content_en)
        if n:
            article.content_en = new_content_en
            changed = True
        translations = dict(article.translations or {})
        for lang_code, entry in list(translations.items()):
            if not isinstance(entry, dict):
                continue
            new, n = _rewrite(entry.get("content", ""))
            if n:
                entry["content"] = new
                translations[lang_code] = entry
                changed = True
        if changed:
            article.translations = translations
            article.save(update_fields=["content_en", "translations"])


def noop(apps, schema_editor):
    """Reverse: cannot reliably reverse partial rewrites — leave forward-only."""


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0004_article_relevant_tool"),
    ]

    operations = [
        migrations.RunPython(fix_links, noop),
    ]
