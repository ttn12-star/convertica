# Generated migration for JSONField-based translations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        # Add translations field to ArticleCategory
        migrations.AddField(
            model_name='articlecategory',
            name='translations',
            field=models.JSONField(blank=True, default=dict, help_text='Translations for other languages. Format: {"ru": {"name": "...", "description": "..."}, ...}', verbose_name='Translations'),
        ),
        
        # Add translations field to Article
        migrations.AddField(
            model_name='article',
            name='translations',
            field=models.JSONField(blank=True, default=dict, help_text='Translations for other languages. Format: {"ru": {"title": "...", "content": "...", ...}, ...}', verbose_name='Translations'),
        ),
        
        # Add AI metadata field to Article
        migrations.AddField(
            model_name='article',
            name='ai_metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Additional metadata for AI agents: topics, entities, summary, related_terms, etc.', verbose_name='AI Metadata'),
        ),
    ]

