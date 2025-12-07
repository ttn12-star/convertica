"""Forms for blog admin."""

import json

from django import forms
from django.conf import settings

from .models import Article, ArticleCategory
from .widgets import AIMetadataWidget, TranslationsWidget


class ArticleAdminForm(forms.ModelForm):
    """Custom form for Article admin with translation handling."""

    class Meta:
        model = Article
        fields = "__all__"
        widgets = {
            "translations": TranslationsWidget(field_type="article"),
            "ai_metadata": AIMetadataWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure widgets are set
        self.fields["translations"].widget = TranslationsWidget(field_type="article")
        self.fields["ai_metadata"].widget = AIMetadataWidget()

    def clean_translations(self):
        """Clean and validate translations field."""
        translations = self.cleaned_data.get("translations")

        # Handle case where widget sends individual fields via hidden input
        # The widget creates a hidden input with JSON, so we check that first
        data = self.data

        # First, try to get from hidden field (widget's JSON output)
        hidden_field_name = "translations"
        if hidden_field_name in data:
            try:
                json_value = data[hidden_field_name]
                if json_value:
                    parsed = json.loads(json_value)
                    if parsed:
                        return parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: check individual fields (if widget sends them separately)
        if data:
            translations_dict = {}
            languages = [lang[0] for lang in settings.LANGUAGES if lang[0] != "en"]

            for lang in languages:
                lang_data = {}
                # For articles: title, content, excerpt, meta_title, meta_description, meta_keywords
                fields = [
                    "title",
                    "content",
                    "excerpt",
                    "meta_title",
                    "meta_description",
                    "meta_keywords",
                ]

                for field in fields:
                    field_key = f"translations_{lang}_{field}"
                    if field_key in data:
                        value = data[field_key]
                        if value and value.strip():
                            lang_data[field] = value.strip()

                if lang_data:
                    translations_dict[lang] = lang_data

            if translations_dict:
                return translations_dict

        # If translations is a string, parse it
        if isinstance(translations, str) and translations.strip():
            try:
                parsed = json.loads(translations)
                return parsed if parsed else {}
            except json.JSONDecodeError:
                return {}

        return translations if translations else {}


class ArticleCategoryAdminForm(forms.ModelForm):
    """Custom form for ArticleCategory admin."""

    class Meta:
        model = ArticleCategory
        fields = "__all__"
        widgets = {
            "translations": TranslationsWidget(field_type="category"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["translations"].widget = TranslationsWidget(field_type="category")

    def clean_translations(self):
        """Clean and validate translations field."""
        translations = self.cleaned_data.get("translations")

        # Handle case where widget sends JSON via hidden field
        data = self.data

        # First, try to get from hidden field (widget's JSON output)
        hidden_field_name = "translations"
        if hidden_field_name in data:
            try:
                json_value = data[hidden_field_name]
                if json_value:
                    parsed = json.loads(json_value)
                    if parsed:
                        return parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: check individual fields
        if data:
            translations_dict = {}
            languages = [lang[0] for lang in settings.LANGUAGES if lang[0] != "en"]

            for lang in languages:
                lang_data = {}
                fields = ["name", "description"]

                for field in fields:
                    field_key = f"translations_{lang}_{field}"
                    if field_key in data:
                        value = data[field_key]
                        if value and value.strip():
                            lang_data[field] = value.strip()

                if lang_data:
                    translations_dict[lang] = lang_data

            if translations_dict:
                return translations_dict

        if isinstance(translations, str) and translations.strip():
            try:
                parsed = json.loads(translations)
                return parsed if parsed else {}
            except json.JSONDecodeError:
                return {}

        return translations if translations else {}
