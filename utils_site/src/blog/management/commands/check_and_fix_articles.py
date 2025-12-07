"""Management command to check and fix article translations and formatting."""

import re

from django.core.management.base import BaseCommand
from django.utils.translation import activate, get_language
from src.blog.models import Article


class Command(BaseCommand):
    help = "Check and fix article translations and formatting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Actually fix the issues (default: only check)",
        )

    def clean_html_content(self, content):
        """Clean HTML content from excessive whitespace."""
        if not content:
            return content

        # Remove excessive newlines (more than 2 consecutive)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove spaces before closing tags
        content = re.sub(r" +</", "</", content)

        # Remove spaces after opening tags
        content = re.sub(r"> +", ">", content)

        # Clean up spaces around tags
        content = re.sub(r">\s+<", "><", content)

        # But preserve intentional spacing in paragraphs
        content = re.sub(r"><p>", ">\n<p>", content)
        content = re.sub(r"</p><", "</p>\n<", content)

        # Remove trailing whitespace from lines
        lines = content.split("\n")
        lines = [line.rstrip() for line in lines]
        content = "\n".join(lines)

        return content.strip()

    def handle(self, *args, **options):
        fix = options["fix"]

        articles = Article.objects.all()
        total_articles = articles.count()

        self.stdout.write(
            self.style.SUCCESS(f"\n=== Checking {total_articles} articles ===\n")
        )

        issues_found = 0
        fixed_count = 0

        for article in articles:
            self.stdout.write(f"\n📄 Article: {article.title_en[:60]}...")
            self.stdout.write(f"   Slug: {article.slug}")

            # Check translations
            if not article.translations:
                self.stdout.write(self.style.WARNING("   ⚠️  No translations found"))
                issues_found += 1
                continue

            # Check each language
            for lang_code in ["ru", "pl", "hi", "es", "id"]:
                if lang_code not in article.translations:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Missing translation for {lang_code}")
                    )
                    issues_found += 1
                    continue

                trans = article.translations[lang_code]

                # Check if content exists
                if "content" not in trans or not trans["content"]:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ {lang_code}: Content missing")
                    )
                    issues_found += 1
                else:
                    content = trans["content"]
                    original_length = len(content)

                    # Check for excessive whitespace
                    if "\n\n\n" in content or "  " in content:
                        self.stdout.write(
                            self.style.WARNING(
                                f"   ⚠️  {lang_code}: Excessive whitespace found"
                            )
                        )
                        issues_found += 1

                        if fix:
                            cleaned = self.clean_html_content(content)
                            trans["content"] = cleaned
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"   ✅ {lang_code}: Cleaned (was {original_length} chars, now {len(cleaned)} chars)"
                                )
                            )
                            fixed_count += 1

            # Clean English content too
            if article.content_en:
                original_length = len(article.content_en)
                if "\n\n\n" in article.content_en or "  " in article.content_en:
                    self.stdout.write(
                        self.style.WARNING("   ⚠️  English: Excessive whitespace found")
                    )
                    issues_found += 1

                    if fix:
                        article.content_en = self.clean_html_content(article.content_en)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ English: Cleaned (was {original_length} chars, now {len(article.content_en)} chars)"
                            )
                        )
                        fixed_count += 1

            # Save if fixing
            if fix and (fixed_count > 0 or issues_found > 0):
                article.save()
                self.stdout.write(self.style.SUCCESS("   💾 Saved"))

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n=== Summary ==="))
        self.stdout.write(f"Total articles checked: {total_articles}")
        self.stdout.write(f"Issues found: {issues_found}")

        if fix:
            self.stdout.write(self.style.SUCCESS(f"Fixed: {fixed_count}"))
            self.stdout.write(self.style.SUCCESS("\n✅ All fixes applied!"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  Run with --fix to apply fixes"))
