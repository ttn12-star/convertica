"""
Template tags for image optimization.
Provides WebP support with fallback and responsive images.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def optimized_image(src, alt="", width=None, height=None, css_class="", loading="lazy"):
    """
    Generate optimized image tag with WebP support and fallback.

    Usage:
        {% optimized_image "images/hero.jpg" "Hero image" width=800 height=600 css_class="rounded-lg" %}

    Args:
        src: Image source path (without extension)
        alt: Alt text for accessibility
        width: Image width in pixels
        height: Image height in pixels
        css_class: CSS classes to apply
        loading: Loading strategy (lazy, eager, auto)

    Returns:
        HTML picture element with WebP and fallback
    """
    # Remove extension if present
    if src.endswith((".jpg", ".jpeg", ".png", ".webp")):
        src_base = src.rsplit(".", 1)[0]
        ext = src.rsplit(".", 1)[1]
    else:
        src_base = src
        ext = "jpg"

    # Build attributes
    attrs = []
    if css_class:
        attrs.append(f'class="{css_class}"')
    if width:
        attrs.append(f'width="{width}"')
    if height:
        attrs.append(f'height="{height}"')
    if loading:
        attrs.append(f'loading="{loading}"')

    attrs_str = " ".join(attrs)

    # Generate picture element
    html = f"""<picture>
  <source srcset="{src_base}.webp" type="image/webp">
  <source srcset="{src_base}.{ext}" type="image/{ext}">
  <img src="{src_base}.{ext}" alt="{alt}" {attrs_str}>
</picture>"""

    return mark_safe(html)


@register.simple_tag
def responsive_image(src, alt="", sizes="100vw", css_class="", loading="lazy"):
    """
    Generate responsive image with srcset for different screen sizes.

    Usage:
        {% responsive_image "images/hero.jpg" "Hero" sizes="(max-width: 768px) 100vw, 50vw" %}

    Args:
        src: Base image source path
        alt: Alt text
        sizes: Sizes attribute for responsive images
        css_class: CSS classes
        loading: Loading strategy

    Returns:
        HTML picture element with responsive srcset
    """
    # Remove extension
    if src.endswith((".jpg", ".jpeg", ".png", ".webp")):
        src_base = src.rsplit(".", 1)[0]
        ext = src.rsplit(".", 1)[1]
    else:
        src_base = src
        ext = "jpg"

    # Generate srcset for different sizes (assuming you have these generated)
    widths = [320, 640, 768, 1024, 1280, 1536, 1920]

    # WebP srcset
    webp_srcset = ", ".join([f"{src_base}-{w}.webp {w}w" for w in widths])

    # Fallback srcset
    fallback_srcset = ", ".join([f"{src_base}-{w}.{ext} {w}w" for w in widths])

    # Build attributes
    attrs = []
    if css_class:
        attrs.append(f'class="{css_class}"')
    if loading:
        attrs.append(f'loading="{loading}"')

    attrs_str = " ".join(attrs)

    # Generate picture element
    html = f"""<picture>
  <source srcset="{webp_srcset}" sizes="{sizes}" type="image/webp">
  <source srcset="{fallback_srcset}" sizes="{sizes}" type="image/{ext}">
  <img src="{src_base}.{ext}" alt="{alt}" {attrs_str}>
</picture>"""

    return mark_safe(html)
