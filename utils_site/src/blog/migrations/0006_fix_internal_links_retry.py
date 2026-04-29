"""Re-run blog link rewrite as a separate migration.

The first deploy that shipped 0005_fix_internal_links logged
"No migrations to apply" — most likely the prod docker image was built from a
cached layer that predates the migration, so Django never saw it. Releasing
the same logic under a new migration name forces an unambiguous re-application
on the next deploy. Idempotent: if 0005 actually did run, this is a no-op.
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
    fixed = 0
    for article in Article.objects.all().iterator():
        changed = False
        new_content_en, n = _rewrite(article.content_en)
        if n:
            article.content_en = new_content_en
            changed = True
            fixed += n
        translations = dict(article.translations or {})
        for lang_code, entry in list(translations.items()):
            if not isinstance(entry, dict):
                continue
            new, n = _rewrite(entry.get("content", ""))
            if n:
                entry["content"] = new
                translations[lang_code] = entry
                changed = True
                fixed += n
        if changed:
            article.translations = translations
            article.save(update_fields=["content_en", "translations"])
    print(f"  [blog.0006] rewrote {fixed} link(s)")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0005_fix_internal_links"),
    ]

    operations = [
        migrations.RunPython(fix_links, noop),
    ]
