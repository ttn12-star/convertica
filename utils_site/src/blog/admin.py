"""Admin configuration for blog models."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import Article, ArticleCategory
from .widgets import TranslationsWidget, AIMetadataWidget
from .forms import ArticleAdminForm, ArticleCategoryAdminForm


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    """Admin for ArticleCategory model."""
    form = ArticleCategoryAdminForm
    list_display = ['name_en', 'slug', 'article_count', 'translations_preview', 'created_at', 'updated_at']
    search_fields = ['name_en', 'slug']
    prepopulated_fields = {'slug': ('name_en',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name_en', 'slug', 'description_en')
        }),
        (_('Translations'), {
            'fields': ('translations',),
            'description': _('Add translations for other languages using the tabs above.')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def translations_preview(self, obj):
        """Display preview of available translations."""
        if not obj or not obj.translations:
            return format_html(
                '<span style="color: #999; font-style: italic;">{}</span>', 
                _('No translations')
            )
        
        languages = list(obj.translations.keys())
        available_langs = [lang for lang in languages if lang in [l[0] for l in settings.LANGUAGES]]
        
        if not available_langs:
            return format_html(
                '<span style="color: #999; font-style: italic;">{}</span>', 
                _('No valid translations')
            )
        
        lang_names = dict(settings.LANGUAGES)
        badges = []
        for lang in available_langs:
            lang_data = obj.translations.get(lang, {})
            # Check if translation has content
            has_content = any(lang_data.values()) if lang_data else False
            if has_content:
                badges.append(
                    format_html(
                        '<span style="background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-right: 4px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">{}</span>',
                        lang_names.get(lang, lang.upper())
                    )
                )
        
        if not badges:
            return format_html(
                '<span style="color: #999; font-style: italic;">{}</span>', 
                _('Empty translations')
            )
        
        return format_html(''.join(badges))
    translations_preview.short_description = _('Translations')
    
    def article_count(self, obj):
        """Display count of articles in this category."""
        return obj.articles.count()
    article_count.short_description = _('Articles')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin for Article model with multilingual support."""
    form = ArticleAdminForm
    list_display = [
        'title_en', 'category', 'status', 'published_at', 
        'view_count', 'created_at', 'preview_image', 'translations_preview'
    ]
    list_filter = ['status', 'category', 'published_at', 'created_at']
    search_fields = ['title_en', 'slug', 'content_en']
    prepopulated_fields = {'slug': ('title_en',)}
    readonly_fields = ['view_count', 'created_at', 'updated_at', 'preview_image']
    date_hierarchy = 'published_at'
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title_en', 'slug', 'category', 'status', 'published_at')
        }),
        (_('English Content'), {
            'fields': ('content_en', 'excerpt_en')
        }),
        (_('SEO - English'), {
            'fields': ('meta_title_en', 'meta_description_en', 'meta_keywords_en'),
            'classes': ('collapse',)
        }),
        (_('Translations'), {
            'fields': ('translations',),
            'description': _('Add translations for other languages using the tabs above. Each language has its own tab with all necessary fields.')
        }),
        (_('AI Metadata'), {
            'fields': ('ai_metadata',),
            'classes': ('collapse',),
            'description': _('Additional metadata for AI agents to better understand and index your content.')
        }),
        (_('Media'), {
            'fields': ('featured_image', 'preview_image')
        }),
        (_('Statistics'), {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def preview_image(self, obj):
        """Display preview of featured image."""
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.featured_image.url
            )
        return _('No image')
    preview_image.short_description = _('Preview')

    def translations_preview(self, obj):
        """Display preview of available translations."""
        if not obj.translations:
            return format_html('<span style="color: #999;">{}</span>', _('No translations'))
        
        languages = list(obj.translations.keys())
        available_langs = [lang for lang in languages if lang in [l[0] for l in settings.LANGUAGES]]
        
        if not available_langs:
            return format_html('<span style="color: #999;">{}</span>', _('No valid translations'))
        
        lang_names = dict(settings.LANGUAGES)
        badges = []
        for lang in available_langs:
            badges.append(
                format_html(
                    '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-right: 4px;">{}</span>',
                    lang_names.get(lang, lang.upper())
                )
            )
        return format_html(''.join(badges))
    translations_preview.short_description = _('Translations')

    def save_model(self, request, obj, form, change):
        """Auto-set published_at when status changes to published."""
        if obj.status == 'published' and not obj.published_at:
            from django.utils import timezone
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)
