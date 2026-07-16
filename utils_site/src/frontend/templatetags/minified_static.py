"""Template tags for serving minified static files in production."""

import functools

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static
from django.utils.safestring import mark_safe

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


@functools.lru_cache(maxsize=8)
def _read_static_css(path):
    content = None
    if not settings.DEBUG:
        # The hashed copy: ManifestStaticFilesStorage has already rewritten its
        # url() refs to the hashed names of the referenced files, so the inlined
        # CSS points at the same URLs as {% static %} (e.g. the font preloads).
        stored = getattr(staticfiles_storage, "stored_name", lambda p: p)(path)
        try:
            with staticfiles_storage.open(stored) as f:
                content = f.read().decode("utf-8")
        except (OSError, ValueError):
            content = None  # no collectstatic yet (tests/CI) — use the source
    if content is None:
        with open(finders.find(path), encoding="utf-8") as f:
            content = f.read()
    # Relative url() refs resolve against the page URL once inlined — absolutize.
    for q in ("'", '"', ""):
        content = content.replace(f"url({q}../", f"url({q}{settings.STATIC_URL}")
    return content


@register.simple_tag
def inline_static(path):
    """
    Return the contents of a static CSS file for inlining into a <style> tag.

    Inlining the single render-blocking stylesheet removes the last blocking
    request from the critical path (~300-400 ms LCP/FCP on PSI mobile).
    Cached per-process; a deploy restarts workers, so staleness is bounded.
    """
    return mark_safe(_read_static_css(path))
