"""
Template tags for i18n utilities.
"""

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def remove_language_prefix(path):
    """
    Remove language prefix from URL path.
    Example: /en/all-tools/ -> /all-tools/
    """
    if not path:
        return path

    # Ensure path is a string, not bytes
    if isinstance(path, bytes):
        try:
            path = path.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            # Fallback to latin-1 if utf-8 fails
            try:
                path = path.decode("latin-1")
            except (UnicodeDecodeError, AttributeError):
                # Ultimate fallback: return as is
                return path

    # Convert to string if not already
    path = str(path)

    # Remove leading slash if present
    path = path.lstrip("/")

    # Check if path starts with language code
    for lang_code, _ in settings.LANGUAGES:
        if path.startswith(f"{lang_code}/"):
            return "/" + path[len(lang_code) + 1 :]
        elif path == lang_code:
            return "/"

    # No language prefix found, return as is
    return "/" + path if not path.startswith("/") else path
