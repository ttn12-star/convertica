#!/usr/bin/env python3
"""
Generate robots.txt with dynamic values during deployment.

Reads the template robots.txt from static/, replaces the sitemap host with
SITE_DOMAIN, and writes the result to staticfiles/ for nginx to serve.

Fails HARD when the template is missing: a hand-rolled fallback here used to
drift from static/robots.txt and would silently un-block /premium/ and
/batch-converter/ if it ever shipped. static/robots.txt is the single source
of truth; a missing template is a build error, not something to paper over.
"""

import os
import sys
from pathlib import Path


def generate_robots_txt():
    """Generate robots.txt with dynamic SITE_DOMAIN."""
    site_domain = os.environ.get("SITE_DOMAIN", "convertica.net")

    base_dir = Path(__file__).resolve().parent.parent
    template_path = base_dir / "static" / "robots.txt"
    output_path = base_dir / "staticfiles" / "robots.txt"

    if not template_path.exists():
        print(f"❌ robots.txt template missing at {template_path}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    content = content.replace(
        "https://convertica.net/sitemap.xml",
        f"https://{site_domain}/sitemap.xml",
    )
    content = content.replace(
        "http://convertica.net/sitemap.xml",
        f"https://{site_domain}/sitemap.xml",
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated robots.txt at {output_path}")
    print(f"   Sitemap: https://{site_domain}/sitemap.xml")
    return 0


if __name__ == "__main__":
    sys.exit(generate_robots_txt())
