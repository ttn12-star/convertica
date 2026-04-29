"""Rewrite category-root tool links in YAML blog source files.

The migration `blog/0005_fix_internal_links` and its retry `0006` patch DB
content, but `import_blog_articles` runs on every deploy and overwrites those
fields from the YAML source — so the bad links come back. This script patches
the YAML source so the importer feeds correct content into the DB.

Patterns are the same as in `blog/management/commands/fix_blog_internal_links.py`.
Idempotent: running twice is a no-op.

Usage:
    python scripts/fix_blog_yaml_links.py            # dry run (default)
    python scripts/fix_blog_yaml_links.py --apply    # write changes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LANG_PREFIX = r"/(?:[a-z]{2}/)?"
PATTERNS: list[tuple[str, str]] = [
    (rf'(href=")({LANG_PREFIX})pdf-edit/?(")', r"\1\2pdf-edit/rotate/\3"),
    (rf'(href=")({LANG_PREFIX})pdf-organize/?(")', r"\1\2pdf-organize/merge/\3"),
    (rf'(href=")({LANG_PREFIX})pdf-security/?(")', r"\1\2pdf-security/protect/\3"),
    (rf'(href=")({LANG_PREFIX})image/?(")', r"\1\2image/optimize/\3"),
]


def rewrite(text: str) -> tuple[str, int]:
    """Apply all patterns to `text`. Return (new_text, replacement_count)."""
    if not text:
        return text, 0
    total = 0
    for pat, repl in PATTERNS:
        text, n = re.subn(pat, repl, text)
        total += n
    return text, total


def walk_yaml(root: Path):
    yield from sorted(root.glob("**/*.yaml"))
    yield from sorted(root.glob("**/*.yml"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes back to disk. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--root",
        default="content/blog_articles",
        help="Directory tree to scan (default: content/blog_articles)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    files_changed = 0
    total_replacements = 0
    for path in walk_yaml(root):
        original = path.read_text(encoding="utf-8")
        new, n = rewrite(original)
        if n == 0:
            continue
        files_changed += 1
        total_replacements += n
        print(f"  {path}: {n} replacement(s)")
        if args.apply:
            path.write_text(new, encoding="utf-8")

    verb = "Updated" if args.apply else "Would update"
    print(
        f"\n{verb} {files_changed} file(s), {total_replacements} replacement(s) total."
    )
    if not args.apply and files_changed:
        print("Dry run. Re-run with --apply to save changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
