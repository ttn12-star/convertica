"""Template tags for serving minified static files in production."""

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def minified_static(path):
    """
    Return minified version of static file in production, original in debug mode.

    Usage: {% minified_static 'js/utils.js' %}
    Returns: 'js/utils.min.js' in production, 'js/utils.js' in debug mode
    """
    # In debug mode, use original files for easier debugging
    if settings.DEBUG:
        return static(path)

    # In production, use minified version if it's a JS file
    if path.endswith(".js") and not path.endswith(".min.js"):
        minified_path = path.replace(".js", ".min.js")
        return static(minified_path)

    return static(path)
