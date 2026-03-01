#!/usr/bin/env python3
"""
Generate robots.txt with dynamic values during deployment.

This script reads the template robots.txt from static/ directory,
replaces placeholders with environment variables, and writes the result
to staticfiles/ directory for nginx to serve.
"""

import os
import sys
from pathlib import Path


def generate_robots_txt():
    """Generate robots.txt with dynamic ADMIN_URL_PATH and SITE_DOMAIN."""
    # Get environment variables
    admin_path = os.environ.get("ADMIN_URL_PATH", "admin")
    site_domain = os.environ.get("SITE_DOMAIN", "convertica.net")

    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    template_path = base_dir / "static" / "robots.txt"
    output_path = base_dir / "staticfiles" / "robots.txt"

    # Ensure staticfiles directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Read template
        if not template_path.exists():
            print(f"Warning: Template not found at {template_path}")
            # Create fallback robots.txt
            content = generate_fallback_content(admin_path, site_domain)
        else:
            with open(template_path, encoding="utf-8") as f:
                content = f.read()

            # Replace placeholders
            content = content.replace("/__ADMIN_PATH__/", f"/{admin_path}/")
            content = content.replace(
                "https://convertica.net/sitemap.xml",
                f"https://{site_domain}/sitemap.xml",
            )
            content = content.replace(
                "http://convertica.net/sitemap.xml",
                f"https://{site_domain}/sitemap.xml",
            )

        # Write to staticfiles
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Generated robots.txt at {output_path}")
        print(f"   Admin path: /{admin_path}/")
        print(f"   Sitemap: https://{site_domain}/sitemap.xml")
        return 0

    except Exception as e:
        print(f"❌ Error generating robots.txt: {e}", file=sys.stderr)
        # Create fallback anyway to ensure robots.txt exists
        try:
            content = generate_fallback_content(admin_path, site_domain)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"⚠️  Created fallback robots.txt at {output_path}")
        except Exception as fallback_error:
            print(f"❌ Failed to create fallback: {fallback_error}", file=sys.stderr)
            return 1
        return 0


def generate_fallback_content(admin_path: str, site_domain: str) -> str:
    """Generate fallback robots.txt content."""
    return f"""User-agent: *
Allow: /

# Duplicate URL variants and internal search/filter combinations
Disallow: /*?lang=*
Disallow: /*&lang=*
Disallow: /*?q=*
Disallow: /*&q=*
Disallow: /*?category=*
Disallow: /*&category=*

# Disallow admin and API endpoints
Disallow: /{admin_path}/
Disallow: /api/
Disallow: /static/admin/

# Disallow user authentication and account pages
Disallow: /users/
Disallow: /*/users/
Disallow: /accounts/
Disallow: /*/accounts/

# Disallow payment and post-conversion success pages
Disallow: /payments/
Disallow: /*/payments/
Disallow: /contribute/success/
Disallow: /*/contribute/success/

# Allow static files
Allow: /static/
Allow: /media/

# Sitemap
Sitemap: https://{site_domain}/sitemap.xml
"""


if __name__ == "__main__":
    sys.exit(generate_robots_txt())
