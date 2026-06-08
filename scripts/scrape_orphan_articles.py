#!/usr/bin/env python3
"""Reconstruct DB-only ("orphan") blog articles from the live site into YAML.

These articles exist in the production DB but were never committed as YAML
source. Because ``import_blog_articles`` overwrites the DB from YAML on every
deploy, they need a faithful YAML representation in ``content/blog_articles/``
so they survive and become editable in code.

For each slug, this fetches all 7 language versions from convertica.net,
extracts the authored fields (title, meta title/description/keywords, excerpt,
and the inner HTML of ``div.article-content``), and writes:

    content/blog_articles/en/<slug>.yaml         (full base front-matter)
    content/blog_articles/<lang>/<slug>.yaml     (translation fields)

Category and relevant_tool are taken from the SLUGS map below (category was
confirmed against the live ?category= listings, so the import does not move an
article to a different section). ai_metadata is auto-built from the scraped
meta fields and can be enriched later.

    python scripts/scrape_orphan_articles.py            # all orphans
    python scripts/scrape_orphan_articles.py <slug> ... # only the given slugs
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import lxml.html
import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "blog_articles"
BASE_URL = "https://convertica.net"
LANGS = ["en", "ru", "pl", "hi", "es", "id", "ar"]

# slug -> (category_slug confirmed live, relevant_tool)
SLUGS = {
    "complete-guide-pdf-to-word-conversion": ("pdf-guides", "pdf_to_word"),
    "ultimate-guide-pdf-compression-reduce-file-size": ("pdf-guides", "compress_pdf"),
    "pdf-to-jpg-converter-online-free": ("pdf-tools-comparison", "pdf_to_jpg"),
    "word-to-pdf-converter-online-free-2025": ("pdf-tools-comparison", "word_to_pdf"),
    "smallpdf-alternative-free-pdf-converter": ("pdf-tools-comparison", "all_tools"),
    "ilovepdf-alternative-free-pdf-tools-2025": ("pdf-tools-comparison", "all_tools"),
    "is-convertica-safe-pdf-file-security-privacy-explained": (
        "security-privacy",
        "protect_pdf",
    ),
    "convertica-launch-update-testing-phase-upcoming-features": (
        "news-updates",
        "all_tools",
    ),
    "convertica-major-release-premium-heroes-new-features-upgrades": (
        "news-updates",
        "all_tools",
    ),
}


def fetch(url: str) -> str:
    out = subprocess.run(
        ["curl", "-sL", "--compressed", "--max-time", "40", url],
        capture_output=True,
        text=True,
    )
    return out.stdout


def _text(doc, xpath: str) -> str:
    r = doc.xpath(xpath)
    if not r:
        return ""
    val = r[0]
    return (val if isinstance(val, str) else val.text_content()).strip()


def _inner_html(el) -> str:
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(lxml.html.tostring(child, encoding="unicode"))
    return "".join(parts).strip()


def scrape_lang(slug: str, lang: str) -> dict | None:
    html = fetch(f"{BASE_URL}/{lang}/blog/{slug}/")
    if not html or "article-content" not in html:
        return None
    doc = lxml.html.document_fromstring(html)
    content_els = doc.xpath('//div[contains(@class,"article-content")]')
    if not content_els:
        return None
    title = _text(doc, "//h1")
    return {
        "title": title,
        "meta_title": _text(doc, "//title"),
        "meta_description": _text(doc, '//meta[@name="description"]/@content'),
        "meta_keywords": _text(doc, '//meta[@name="keywords"]/@content'),
        "excerpt": _text(doc, '//meta[@property="og:description"]/@content'),
        "content": _inner_html(content_els[0]),
    }


def yaml_scalar(key: str, value: str) -> str:
    """One `key: value` line, safely quoted by PyYAML."""
    return yaml.safe_dump(
        {key: value}, allow_unicode=True, default_flow_style=False, width=10**9
    ).rstrip("\n")


def block_scalar(key: str, value: str) -> str:
    body = "\n".join("  " + line for line in value.split("\n"))
    return f"{key}: |\n{body}"


def build_ai_metadata(fields: dict) -> dict:
    kws = [k.strip() for k in fields["meta_keywords"].split(",") if k.strip()]
    words = len(fields["content"].split())
    return {
        "topics": kws[:5],
        "entities": ["Convertica", "PDF"],
        "summary": fields["meta_description"] or fields["excerpt"],
        "related_terms": kws[5:13],
        "reading_time_minutes": max(1, round(words / 200)),
        "target_audience": "Users looking for clear, practical PDF guidance.",
    }


def write_base(slug: str, category: str, tool: str, f: dict) -> Path:
    ai = build_ai_metadata(f)
    lines = [
        f"slug: {slug}",
        f"cover_image: blog/images/cover-{slug}.jpg",
        "status: published",
        f"category_slug: {category}",
        f"relevant_tool: {tool}",
        yaml_scalar("title_en", f["title"]),
        yaml_scalar("meta_title_en", f["meta_title"]),
        yaml_scalar("meta_description_en", f["meta_description"]),
        yaml_scalar("meta_keywords_en", f["meta_keywords"]),
        yaml_scalar("excerpt_en", f["excerpt"]),
        "ai_metadata:",
        *(
            "  " + line
            for line in yaml.safe_dump(
                ai, allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            .rstrip("\n")
            .split("\n")
        ),
        block_scalar("content_en", f["content"]),
        "",
    ]
    path = OUT / "en" / f"{slug}.yaml"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_translation(slug: str, lang: str, f: dict) -> Path:
    lines = [
        f"slug: {slug}",
        yaml_scalar(f"title_{lang}", f["title"]),
        yaml_scalar(f"meta_title_{lang}", f["meta_title"]),
        yaml_scalar(f"meta_description_{lang}", f["meta_description"]),
        yaml_scalar(f"meta_keywords_{lang}", f["meta_keywords"]),
        yaml_scalar(f"excerpt_{lang}", f["excerpt"]),
        block_scalar(f"content_{lang}", f["content"]),
        "",
    ]
    path = OUT / lang / f"{slug}.yaml"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    slugs = argv or list(SLUGS)
    for slug in slugs:
        if slug not in SLUGS:
            print(f"  ! unknown slug: {slug}", file=sys.stderr)
            continue
        category, tool = SLUGS[slug]
        print(f"\n=== {slug}  [{category} / {tool}]")
        for lang in LANGS:
            f = scrape_lang(slug, lang)
            if not f or not f["title"] or not f["content"]:
                print(f"  ! {lang}: MISSING (no content extracted)")
                continue
            if lang == "en":
                p = write_base(slug, category, tool, f)
            else:
                p = write_translation(slug, lang, f)
            wc = len(f["content"].split())
            print(f"  + {lang}: {p.relative_to(ROOT)}  ({wc} words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
