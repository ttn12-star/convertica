#!/usr/bin/env python3
"""
Script to apply rate limiting to all batch_views.py files.
Adds combined_rate_limit decorator with stricter limits for batch operations.
"""

import re
from pathlib import Path

# Batch views files to update
BATCH_FILES = [
    "utils_site/src/api/html_convert/batch_views.py",
    "utils_site/src/api/pdf_convert/excel_to_pdf/batch_views.py",
    "utils_site/src/api/pdf_convert/jpg_to_pdf/batch_views.py",
    "utils_site/src/api/pdf_convert/pdf_to_excel/batch_views.py",
    "utils_site/src/api/pdf_convert/pdf_to_html/batch_views.py",
    "utils_site/src/api/pdf_convert/pdf_to_jpg/batch_views.py",
    "utils_site/src/api/pdf_convert/pdf_to_ppt/batch_views.py",
    "utils_site/src/api/pdf_convert/pdf_to_word/batch_views.py",
    "utils_site/src/api/pdf_convert/ppt_to_pdf/batch_views.py",
    "utils_site/src/api/pdf_convert/word_to_pdf/batch_views.py",
    "utils_site/src/api/pdf_edit/add_page_numbers/batch_views.py",
    "utils_site/src/api/pdf_edit/add_watermark/batch_views.py",
    "utils_site/src/api/pdf_edit/crop_pdf/batch_views.py",
    "utils_site/src/api/pdf_organize/compress_pdf/batch_views.py",
    "utils_site/src/api/pdf_organize/extract_pages/batch_views.py",
    "utils_site/src/api/pdf_organize/organize_pdf/batch_views.py",
    "utils_site/src/api/pdf_organize/remove_pages/batch_views.py",
    "utils_site/src/api/pdf_organize/split_pdf/batch_views.py",
    "utils_site/src/api/pdf_security/protect_pdf/batch_views.py",
    "utils_site/src/api/pdf_security/unlock_pdf/batch_views.py",
]

IMPORT_TO_ADD = "from src.api.rate_limit_utils import combined_rate_limit"
DECORATOR_TO_ADD = (
    "    @combined_rate_limit(group='api_batch', ip_rate='10/h', methods=['POST'])"
)
DOCSTRING_ADDITION = """

        Rate limits (batch operations - stricter):
        - IP: 10 requests/hour
        - Anonymous: 0/h (blocked), Authenticated: 50/h, Premium: 500/h"""


def add_import_if_missing(content, filepath):
    """Add rate_limit_utils import if not present."""
    if "from src.api.rate_limit_utils import combined_rate_limit" in content:
        print(f"  ✓ Import already exists in {filepath}")
        return content

    # Find the last import statement
    lines = content.split("\n")
    last_import_idx = -1

    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            last_import_idx = i

    if last_import_idx >= 0:
        # Insert after last import
        lines.insert(last_import_idx + 1, IMPORT_TO_ADD)
        print(f"  ✓ Added import to {filepath}")
        return "\n".join(lines)

    print(f"  ⚠ Could not find import section in {filepath}")
    return content


def add_decorator_to_post_method(content, filepath):
    """Add rate limiting decorator before post method."""
    if "@combined_rate_limit(group='api_batch'" in content:
        print(f"  ✓ Decorator already exists in {filepath}")
        return content

    # Find post method definition
    # Pattern: any decorator followed by "def post(self, request"
    pattern = r"(\s+)(@\w+.*\n)?(\s+def post\(self, request)"

    def replace_func(match):
        indent = match.group(1)
        existing_decorator = match.group(2) or ""
        method_def = match.group(3)

        # Add our decorator before existing decorator or method
        return f"{DECORATOR_TO_ADD}\n{indent}{existing_decorator}{method_def}"

    new_content = re.sub(pattern, replace_func, content)

    if new_content != content:
        print(f"  ✓ Added decorator to {filepath}")
        return new_content

    print(f"  ⚠ Could not find post method in {filepath}")
    return content


def add_docstring_note(content, filepath):
    """Add rate limit note to post method docstring."""
    if "Rate limits (batch operations" in content:
        print(f"  ✓ Docstring note already exists in {filepath}")
        return content

    # Find docstring after post method
    pattern = r'(def post\(self, request[^:]*:\s*\n\s+"""[^"]+""")'

    def replace_func(match):
        docstring = match.group(1)
        # Add note before closing """
        return docstring.replace('"""', f'{DOCSTRING_ADDITION}\n        """')

    new_content = re.sub(pattern, replace_func, content)

    if new_content != content:
        print(f"  ✓ Added docstring note to {filepath}")

    return new_content


def process_file(filepath):
    """Process a single batch_views.py file."""
    full_path = Path(filepath)

    if not full_path.exists():
        print(f"✗ File not found: {filepath}")
        return False

    print(f"\n📝 Processing: {filepath}")

    # Read file
    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Apply transformations
    content = add_import_if_missing(content, filepath)
    content = add_decorator_to_post_method(content, filepath)
    content = add_docstring_note(content, filepath)

    # Write back if changed
    if content != original_content:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ Updated {filepath}")
        return True
    else:
        print(f"○ No changes needed for {filepath}")
        return False


def main():
    """Main function to process all batch files."""
    print("🚀 Applying rate limiting to batch endpoints...")
    print(f"📊 Found {len(BATCH_FILES)} batch files to process\n")

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for filepath in BATCH_FILES:
        try:
            if process_file(filepath):
                updated_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"✗ Error processing {filepath}: {e}")
            error_count += 1

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"  ✓ Updated: {updated_count}")
    print(f"  ○ Skipped (already done): {skipped_count}")
    print(f"  ✗ Errors: {error_count}")
    print(f"  📁 Total: {len(BATCH_FILES)}")
    print("=" * 60)

    if updated_count > 0:
        print("\n✅ Rate limiting applied successfully!")
        print("\n📝 Next steps:")
        print("  1. Review changes: git diff")
        print("  2. Test endpoints: python manage.py runserver")
        print("  3. Check rate limits: python manage.py rate_limit_stats")
    else:
        print("\n✅ All batch endpoints already have rate limiting!")


if __name__ == "__main__":
    main()
