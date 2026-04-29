"""SEO-related template filters."""

from django import template

register = template.Library()


_TRAILING_PUNCT = " \t\n\r,.;:!?-—–"


@register.filter
def seo_meta(value, max_len: int = 155) -> str:
    """Trim a meta description to max_len chars on a word boundary.

    Google truncates meta description ~155-160 chars. Same string flows to og:/
    twitter: tags so this filter is idempotent for anything ≤ max_len.

    Trailing punctuation/whitespace from the cut point is stripped so we don't
    leave dangling commas or em-dashes.
    """
    if not value:
        return value
    text = str(value).strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    last_space = cut.rfind(" ")
    if last_space >= max_len * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(_TRAILING_PUNCT)


@register.filter
def seo_title(value, max_len: int = 60) -> str:
    """Trim a page title to max_len chars while preserving a `| Brand` suffix.

    Google shows ~60 chars in SERP. If the input has a trailing `| <Brand>`
    or `- <Brand>` suffix, we keep it and shorten only the body so that the
    brand stays visible. Trailing word boundary cuts.
    """
    if not value:
        return value
    text = str(value).strip()
    if len(text) <= max_len:
        return text
    suffix = ""
    for sep in (" | ", " — ", " - "):
        idx = text.rfind(sep)
        if idx > 0 and len(text) - idx <= 25:
            suffix = text[idx:]
            text = text[:idx]
            break
    budget = max_len - len(suffix)
    if budget < 20:
        # Brand suffix too long for budget; fall back to plain trim.
        return seo_meta(str(value).strip(), max_len)
    if len(text) > budget:
        cut = text[:budget]
        last_space = cut.rfind(" ")
        if last_space >= budget * 0.6:
            cut = cut[:last_space]
        text = cut.rstrip(_TRAILING_PUNCT)
    return text + suffix
