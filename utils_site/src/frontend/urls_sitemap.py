"""URLs for sitemap - separate from i18n_patterns."""

from django.urls import path

from . import views

urlpatterns = [
    # Sitemap index (lists all language-specific sitemaps)
    path("", views.sitemap_index, name="sitemap_index"),
    # Language-specific sitemaps
    path("sitemap-<str:lang>.xml", views.sitemap_lang, name="sitemap_lang"),
]
