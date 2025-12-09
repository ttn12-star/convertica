"""Custom widgets for blog admin."""

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe


class TranslationsWidget(forms.Textarea):
    """Custom widget for editing translations with tabs for each language."""

    template_name = "admin/blog/translations_widget.html"

    def __init__(self, attrs=None, field_type="article"):
        """
        Initialize widget.

        Args:
            attrs: Widget attributes
            field_type: 'article' or 'category' - determines which fields to show
        """
        default_attrs = {"cols": 80, "rows": 20, "class": "translations-widget"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
        self.field_type = field_type
        self.languages = [lang[0] for lang in settings.LANGUAGES if lang[0] != "en"]
        self.language_names = dict(settings.LANGUAGES)

    def format_value(self, value):
        """Format value for display."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        import json

        return json.dumps(value, ensure_ascii=False, indent=2)

    def render(self, name, value, attrs=None, renderer=None):
        """Render widget with tabs for each language."""
        if attrs is None:
            attrs = {}

        # Get current value as dict
        import json

        try:
            if isinstance(value, str) and value:
                translations = json.loads(value)
            elif isinstance(value, dict):
                translations = value
            else:
                translations = {}
        except (json.JSONDecodeError, TypeError):
            translations = {}

        # Build HTML
        output = []
        output.append('<div class="translations-widget-container">')

        # Tabs
        output.append('<div class="translations-tabs">')
        for lang in self.languages:
            lang_name = self.language_names.get(lang, lang.upper())
            active = "active" if lang == self.languages[0] else ""
            output.append(
                f'<button type="button" class="translation-tab {active}" data-lang="{lang}">'
                f"{lang_name}</button>"
            )
        output.append("</div>")

        # Tab content
        output.append('<div class="translations-content">')
        for lang in self.languages:
            lang_name = self.language_names.get(lang, lang.upper())
            display = "block" if lang == self.languages[0] else "none"

            lang_data = translations.get(lang, {})

            output.append(
                f'<div class="translation-panel" data-lang="{lang}" style="display: {display};">'
            )

            if self.field_type == "article":
                # Article fields
                fields = [
                    ("title", "Title", "text"),
                    ("content", "Content", "textarea"),
                    ("excerpt", "Excerpt", "textarea"),
                    ("meta_title", "Meta Title", "text"),
                    ("meta_description", "Meta Description", "textarea"),
                    ("meta_keywords", "Meta Keywords", "text"),
                ]
            else:
                # Category fields
                fields = [
                    ("name", "Name", "text"),
                    ("description", "Description", "textarea"),
                ]

            for field_key, field_label, field_type in fields:
                field_value = lang_data.get(field_key, "")
                # Properly escape HTML for display
                from django.utils.html import escape

                if field_value:
                    # For textarea, don't escape - Django handles it
                    if field_type == "textarea":
                        display_value = str(field_value)
                    else:
                        display_value = escape(str(field_value))
                else:
                    display_value = ""

                field_id = f"id_{name}_{lang}_{field_key}"
                field_name = f"translations_{lang}_{field_key}"

                if field_type == "textarea":
                    output.append(
                        f'<div class="translation-field">'
                        f'<label for="{field_id}">{field_label} ({lang_name}):</label>'
                        f'<textarea id="{field_id}" name="{field_name}" class="form-control" rows="5">{display_value}</textarea>'
                        f"</div>"
                    )
                else:
                    output.append(
                        f'<div class="translation-field">'
                        f'<label for="{field_id}">{field_label} ({lang_name}):</label>'
                        f'<input type="text" id="{field_id}" name="{field_name}" class="form-control" value="{display_value}">'
                        f"</div>"
                    )

            output.append("</div>")

        output.append("</div>")

        # Hidden field for JSON (will be updated by JavaScript)
        hidden_id = f"id_{name}"
        hidden_value = (
            json.dumps(translations, ensure_ascii=False) if translations else "{}"
        )
        # Properly escape for HTML attribute
        import html

        hidden_value_escaped = html.escape(hidden_value)
        output.append(
            f'<input type="hidden" id="{hidden_id}" name="{name}" value="{hidden_value_escaped}">'
        )

        output.append("</div>")

        # Add JavaScript
        output.append(
            """
        <script>
        (function() {
            const container = document.querySelector('.translations-widget-container');
            if (!container) return;

            // Tab switching
            container.querySelectorAll('.translation-tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    const lang = this.dataset.lang;

                    // Update tabs
                    container.querySelectorAll('.translation-tab').forEach(t => t.classList.remove('active'));
                    this.classList.add('active');

                    // Update panels
                    container.querySelectorAll('.translation-panel').forEach(p => {
                        p.style.display = p.dataset.lang === lang ? 'block' : 'none';
                    });
                });
            });

            // Update hidden JSON field on input change
            function updateJSON() {
                const translations = {};
                const panels = container.querySelectorAll('.translation-panel');

                panels.forEach(panel => {
                    const lang = panel.dataset.lang;
                    translations[lang] = {};

                    panel.querySelectorAll('input[type="text"], textarea').forEach(input => {
                        const inputName = input.name;
                        // Match pattern: translations_ru_title, translations_pl_content, etc.
                        const match = inputName.match(/translations_([a-z]{2})_([a-z_]+)$/);
                        if (match && match[1] === lang) {
                            const field = match[2];
                            const value = input.value.trim();
                            if (value) {
                                translations[lang][field] = value;
                            }
                        }
                    });
                });

                const hiddenInput = container.querySelector('input[type="hidden"]');
                if (hiddenInput) {
                    // Only include languages that have at least one field filled
                    const filtered = {};
                    Object.keys(translations).forEach(lang => {
                        if (Object.keys(translations[lang]).length > 0) {
                            filtered[lang] = translations[lang];
                        }
                    });
                    hiddenInput.value = JSON.stringify(filtered);
                }
            }

            container.querySelectorAll('input, textarea').forEach(input => {
                input.addEventListener('input', updateJSON);
                input.addEventListener('change', updateJSON);
            });

            // Initial update
            updateJSON();
        })();
        </script>
        """
        )

        # Add CSS
        output.append(
            """
        <style>
        .translations-widget-container {
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
        }
        .translations-tabs {
            display: flex;
            border-bottom: 2px solid #417690;
            background: #f8f9fa;
        }
        .translation-tab {
            padding: 10px 20px;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            font-weight: 500;
            color: #666;
            transition: all 0.2s;
        }
        .translation-tab:hover {
            background: #e9ecef;
            color: #417690;
        }
        .translation-tab.active {
            color: #417690;
            border-bottom-color: #417690;
            background: #fff;
        }
        .translations-content {
            padding: 20px;
        }
        .translation-panel {
            display: none;
        }
        .translation-panel.active {
            display: block;
        }
        .translation-field {
            margin-bottom: 15px;
        }
        .translation-field label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        .translation-field input,
        .translation-field textarea {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .translation-field textarea {
            min-height: 100px;
            font-family: monospace;
        }
        </style>
        """
        )

        return mark_safe("".join(output))


class AIMetadataWidget(forms.Textarea):
    """Custom widget for editing AI metadata."""

    def __init__(self, attrs=None):
        default_attrs = {"cols": 80, "rows": 15, "class": "ai-metadata-widget"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        """Format value for display."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        import json

        return json.dumps(value, ensure_ascii=False, indent=2)

    def render(self, name, value, attrs=None, renderer=None):
        """Render widget with helpful structure."""
        if attrs is None:
            attrs = {}

        # Get current value
        import json

        try:
            if isinstance(value, str) and value:
                metadata = json.loads(value)
            elif isinstance(value, dict):
                metadata = value
            else:
                metadata = {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        output = []
        output.append('<div class="ai-metadata-widget-container">')

        # Help text
        output.append(
            """
        <div class="ai-metadata-help" style="background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #417690;">
            <strong>AI Metadata Structure:</strong>
            <pre style="margin: 10px 0; font-size: 12px;">{
  "topics": ["PDF", "conversion", "tools"],
  "entities": [{"type": "tool", "name": "Convertica"}],
  "summaries": {
    "en": "Summary in English",
    "ru": "Краткое описание на русском"
  },
  "related_terms": ["PDF converter", "document tools"]
}</pre>
        </div>
        """
        )

        # Textarea for JSON
        textarea_id = f"id_{name}"
        textarea_value = (
            json.dumps(metadata, ensure_ascii=False, indent=2) if metadata else "{}"
        )
        output.append(
            f'<textarea id="{textarea_id}" name="{name}" class="form-control" rows="15" '
            f'style="font-family: monospace; font-size: 13px;">{textarea_value}</textarea>'
        )

        output.append("</div>")

        return mark_safe("".join(output))
