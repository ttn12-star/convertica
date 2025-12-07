"""Blog models for articles and SEO content with JSONField-based multilingual support."""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ArticleCategory(models.Model):
    """Category for blog articles with multilingual support."""

    # Base language (English) - required
    name_en = models.CharField(max_length=100, verbose_name=_("Name (English)"))
    slug = models.SlugField(unique=True, verbose_name=_("Slug"))

    # Translations stored in JSON
    # Structure: {"ru": {"name": "...", "description": "..."}, "pl": {...}, ...}
    translations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Translations"),
        help_text=_(
            'Translations for other languages. Format: {"ru": {"name": "...", "description": "..."}, ...}'
        ),
    )

    # Base description
    description_en = models.TextField(
        blank=True, verbose_name=_("Description (English)")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Article Category")
        verbose_name_plural = _("Article Categories")
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_en)
        super().save(*args, **kwargs)

    def get_name(self, language_code=None):
        """Get category name in specified language or current active language."""
        if language_code is None:
            from django.utils.translation import get_language

            language_code = get_language()

        # Check translations JSON
        if language_code in self.translations:
            trans = self.translations.get(language_code, {})
            if trans.get("name"):
                return trans["name"]

        # Fallback to English
        return self.name_en

    def get_description(self, language_code=None):
        """Get category description in specified language."""
        if language_code is None:
            from django.utils.translation import get_language

            language_code = get_language()

        # Check translations JSON
        if language_code in self.translations:
            trans = self.translations.get(language_code, {})
            if trans.get("description"):
                return trans["description"]

        # Fallback to English
        return self.description_en


class Article(models.Model):
    """Blog article model with JSONField-based multilingual support and AI-optimized structure."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("published", _("Published")),
        ("archived", _("Archived")),
    ]

    # Base language (English) - required fields
    title_en = models.CharField(max_length=200, verbose_name=_("Title (English)"))
    slug = models.SlugField(unique=True, max_length=200, verbose_name=_("Slug"))
    content_en = models.TextField(verbose_name=_("Content (English)"))
    excerpt_en = models.TextField(
        max_length=500, blank=True, verbose_name=_("Excerpt (English)")
    )

    # Translations stored in JSON
    # Structure: {
    #   "ru": {"title": "...", "content": "...", "excerpt": "...", "meta_title": "...", "meta_description": "...", "meta_keywords": "..."},
    #   "pl": {...},
    #   ...
    # }
    translations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Translations"),
        help_text=_(
            'Translations for other languages. Format: {"ru": {"title": "...", "content": "...", ...}, ...}'
        ),
    )

    # SEO fields (base language)
    meta_title_en = models.CharField(
        max_length=200, blank=True, verbose_name=_("Meta Title (English)")
    )
    meta_description_en = models.TextField(
        max_length=500, blank=True, verbose_name=_("Meta Description (English)")
    )
    meta_keywords_en = models.CharField(
        max_length=500, blank=True, verbose_name=_("Meta Keywords (English)")
    )

    # AI-optimized metadata (stored in JSON for flexibility)
    # Can include: topics, entities, summary, related_terms, etc.
    ai_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("AI Metadata"),
        help_text=_(
            "Additional metadata for AI agents: topics, entities, summary, related_terms, etc."
        ),
    )

    # Category
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        verbose_name=_("Category"),
    )

    # Featured image
    featured_image = models.ImageField(
        upload_to="blog/images/",
        blank=True,
        null=True,
        verbose_name=_("Featured Image"),
    )

    # Status and dates
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status")
    )
    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Published At")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # SEO and analytics
    view_count = models.PositiveIntegerField(default=0, verbose_name=_("View Count"))

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["category"]),
            # JSONField indexes for PostgreSQL (if using PostgreSQL)
            # models.Index(fields=['translations'], name='article_translations_idx'),
        ]

    def __str__(self):
        return self.title_en

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Get absolute URL for the article."""
        return reverse("blog:article_detail", kwargs={"slug": self.slug})

    def _get_translation(self, field_name, language_code=None, default_field=None):
        """Helper method to get translated field value."""
        if language_code is None:
            from django.utils.translation import get_language

            language_code = get_language()

        # Check if language is English (base language)
        if language_code == "en" or language_code not in [
            lang[0] for lang in settings.LANGUAGES
        ]:
            if default_field:
                return getattr(self, default_field, "")
            return ""

        # Get from translations JSON
        if language_code in self.translations:
            trans = self.translations.get(language_code, {})
            if field_name in trans and trans[field_name]:
                return trans[field_name]

        # Fallback to English
        if default_field:
            return getattr(self, default_field, "")
        return ""

    def get_title(self, language_code=None):
        """Get title in specified language or current active language."""
        result = self._get_translation("title", language_code, "title_en")
        return result or self.title_en

    def get_content(self, language_code=None):
        """Get content in specified language or current active language."""
        result = self._get_translation("content", language_code, "content_en")
        return result or self.content_en

    def get_excerpt(self, language_code=None):
        """Get excerpt in specified language or current active language."""
        result = self._get_translation("excerpt", language_code, "excerpt_en")
        if result:
            return result
        # Fallback to excerpt_en or first 500 chars of content
        if self.excerpt_en:
            return self.excerpt_en
        return self.get_content(language_code)[:500]

    def get_meta_title(self, language_code=None):
        """Get meta title in specified language or current active language."""
        result = self._get_translation("meta_title", language_code, "meta_title_en")
        if result:
            return result
        # Fallback to title
        return self.get_title(language_code)

    def get_meta_description(self, language_code=None):
        """Get meta description in specified language or current active language."""
        result = self._get_translation(
            "meta_description", language_code, "meta_description_en"
        )
        if result:
            return result
        # Fallback to excerpt
        return self.get_excerpt(language_code)

    def get_meta_keywords(self, language_code=None):
        """Get meta keywords in specified language or current active language."""
        result = self._get_translation(
            "meta_keywords", language_code, "meta_keywords_en"
        )
        return result or self.meta_keywords_en

    def increment_view_count(self):
        """Increment view count asynchronously to avoid blocking requests."""
        # Use F() expression for atomic update to avoid race conditions
        from django.db.models import F

        Article.objects.filter(id=self.id).update(view_count=F("view_count") + 1)
        # Refresh instance from database
        self.refresh_from_db(fields=["view_count"])

    def get_ai_topics(self):
        """Get AI-identified topics for this article."""
        return self.ai_metadata.get("topics", [])

    def get_ai_entities(self):
        """Get AI-identified entities (people, places, organizations) for this article."""
        return self.ai_metadata.get("entities", [])

    def get_ai_summary(self, language_code=None):
        """Get AI-generated summary for this article."""
        if language_code is None:
            from django.utils.translation import get_language

            language_code = get_language()

        summaries = self.ai_metadata.get("summaries", {})
        return summaries.get(language_code, summaries.get("en", ""))
