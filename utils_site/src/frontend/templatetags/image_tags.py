"""Template tags for article/image content."""

import re

from django import template

register = template.Library()

# Block-level tags an article chunk may legitimately start with. A chunk that
# starts with anything else (plain text, or an inline tag like <strong>) is a
# paragraph the author wrote without <p> around it.
_BLOCK_TAGS = (
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "figure",
    "figcaption",
    "pre",
    "blockquote",
    "div",
    "section",
    "aside",
    "hr",
    "img",
    "picture",
    "video",
    "iframe",
    "dl",
    "dt",
    "dd",
    "script",
    "style",
    "details",
    "summary",
)
_BLOCK_START_RE = re.compile(
    r"^<\s*/?\s*(?:" + "|".join(_BLOCK_TAGS) + r")\b", re.IGNORECASE
)


@register.filter(is_safe=True)
def demote_headings(value):
    """Demote <h1> tags to <h2> in article body content to avoid duplicate h1 on the page."""
    value = re.sub(r"<h1(\s|>)", r"<h2\1", value, flags=re.IGNORECASE)
    value = re.sub(r"</h1>", "</h2>", value, flags=re.IGNORECASE)
    return value


# <pre> content is whitespace-significant and code samples contain blank lines,
# so those regions are passed through untouched.
_PRE_BLOCK_RE = re.compile(r"<pre\b.*?</pre>", re.IGNORECASE | re.DOTALL)


def _wrap_chunks(text):
    out = []
    for chunk in re.split(r"\n\s*\n", text):
        stripped = chunk.strip()
        if not stripped:
            continue
        if _BLOCK_START_RE.match(stripped):
            out.append(chunk)
        else:
            out.append(f"<p>{stripped}</p>")
    return "\n\n".join(out)


@register.filter(is_safe=True)
def wrap_bare_paragraphs(value):
    """Wrap blank-line-separated raw text in <p> so it gets paragraph spacing.

    Almost every article opens with one or two intro paragraphs written without
    <p> tags. Those are text nodes, so no stylesheet can put space between them
    and they rendered as one run-on block. Wrapping happens here rather than in
    ~260 YAML files.
    """
    if not value:
        return value

    parts = []
    last = 0
    for match in _PRE_BLOCK_RE.finditer(value):
        parts.append(_wrap_chunks(value[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_wrap_chunks(value[last:]))
    return "\n\n".join(part for part in parts if part)
