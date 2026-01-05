"""Template tags for optimized image loading."""

from django import template
from django.template.loader import render_to_string
from django.templatetags.static import static

register = template.Library()


@register.inclusion_tag("frontend/includes/optimized_image.html")
def optimized_image(
    src,
    alt="",
    width=None,
    height=None,
    loading="lazy",
    fetchpriority="auto",
    class_name="",
    sizes="100vw",
):
    """
    Render an optimized image with lazy loading, proper dimensions, and responsive support.

    Usage:
        {% load image_tags %}
        {% optimized_image "images/hero.jpg" "Hero image" width=800 height=600 fetchpriority="high" %}
        {% optimized_image "images/feature.webp" "Feature" loading="lazy" class_name="rounded-lg" %}

    Args:
        src: Image source (will be passed through static tag)
        alt: Alt text for accessibility
        width: Image width in pixels
        height: Image height in pixels
        loading: 'lazy' (default), 'eager', or 'auto'
        fetchpriority: 'high', 'low', or 'auto' (default)
        class_name: CSS classes
        sizes: Sizes attribute for responsive images

    Features:
        - Lazy loading by default (except for above-the-fold images)
        - Proper width/height to prevent layout shift (CLS)
        - decoding="async" for better performance
        - Support for high-priority images (hero images)
    """
    return {
        "src": static(src),
        "alt": alt,
        "width": width,
        "height": height,
        "loading": loading,
        "fetchpriority": fetchpriority,
        "class_name": class_name,
        "sizes": sizes,
        "has_dimensions": width and height,
    }


@register.simple_tag
def picture_tag(webp_src, fallback_src, alt="", width=None, height=None, **kwargs):
    """
    Generate a <picture> element with WebP and fallback sources.

    Usage:
        {% picture_tag "images/hero.webp" "images/hero.jpg" "Hero" width=800 height=600 fetchpriority="high" %}

    Args:
        webp_src: WebP image source
        fallback_src: Fallback image (JPG/PNG)
        alt: Alt text
        width: Image width
        height: Image height
        **kwargs: Additional attributes (loading, fetchpriority, class_name)

    Returns:
        HTML string with <picture> element
    """
    loading = kwargs.get("loading", "lazy")
    fetchpriority = kwargs.get("fetchpriority", "auto")
    class_name = kwargs.get("class_name", "")

    width_attr = f'width="{width}"' if width else ""
    height_attr = f'height="{height}"' if height else ""
    class_attr = f'class="{class_name}"' if class_name else ""

    html = f"""
    <picture>
      <source srcset="{static(webp_src)}" type="image/webp">
      <source srcset="{static(fallback_src)}" type="image/{fallback_src.split('.')[-1]}">
      <img src="{static(fallback_src)}"
           alt="{alt}"
           {width_attr}
           {height_attr}
           loading="{loading}"
           fetchpriority="{fetchpriority}"
           decoding="async"
           {class_attr}>
    </picture>
    """.strip()

    return html
