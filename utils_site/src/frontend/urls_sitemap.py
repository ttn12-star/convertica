"""URLs for sitemap - separate from i18n_patterns."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.sitemap_xml, name="sitemap_xml"),
]
