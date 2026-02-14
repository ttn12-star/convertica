"""
Template tags for i18n utilities.
"""

from urllib.parse import urlsplit

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def remove_language_prefix(path):
    """
    Remove language prefix from URL path.
    Removes ALL language prefixes, not just the first one.
    Example: /en/all-tools/ -> /all-tools/
    Example: /en/pl/all-tools/ -> /all-tools/ (removes both)
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

    parsed = urlsplit(path)
    # Remove leading slash if present
    path = parsed.path.lstrip("/")

    # Remove ALL language prefixes (in case of double prefixes like /en/pl/...)
    removed_any = True
    while removed_any:
        removed_any = False
        for lang_code, _ in settings.LANGUAGES:
            if path.startswith(f"{lang_code}/"):
                path = path[len(lang_code) + 1 :]
                removed_any = True
                break
            elif path == lang_code:
                path = ""
                removed_any = True
                break

    # Return result
    cleaned_path = "/" + path if path else "/"
    if parsed.query:
        cleaned_path = f"{cleaned_path}?{parsed.query}"
    if parsed.fragment:
        cleaned_path = f"{cleaned_path}#{parsed.fragment}"
    return cleaned_path
