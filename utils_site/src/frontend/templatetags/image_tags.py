"""Template tags for article/image content."""

import re

from django import template

register = template.Library()


@register.filter(is_safe=True)
def demote_headings(value):
    """Demote <h1> tags to <h2> in article body content to avoid duplicate h1 on the page."""
    value = re.sub(r"<h1(\s|>)", r"<h2\1", value, flags=re.IGNORECASE)
    value = re.sub(r"</h1>", "</h2>", value, flags=re.IGNORECASE)
    return value
