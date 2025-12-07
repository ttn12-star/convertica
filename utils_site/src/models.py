"""Models for website tools and utilities."""

from django.db import models


class Tool(models.Model):
    """
    Represents a utility/tool on the website.
    """

    CATEGORY_CHOICES: list[tuple[str, str]] = [
        ("text", "Text"),
        ("pdf", "PDF"),
        ("image", "Image"),
        ("dev", "Developer"),
        ("other", "Other"),
    ]

    LANGUAGE_CHOICES: list[tuple[str, str]] = [
        ("en", "English"),
        ("ru", "Russian"),
    ]

    name: models.CharField = models.CharField(max_length=100)
    slug: models.SlugField = models.SlugField(unique=True)
    description: models.TextField = models.TextField(blank=True)
    category: models.CharField = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES
    )
    language: models.CharField = models.CharField(
        max_length=2, choices=LANGUAGE_CHOICES, default="en"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Return the tool name."""
        return str(self.name)
