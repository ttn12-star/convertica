from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.blog"
    verbose_name = "Blog"

    def ready(self):
        """Import signals when app is ready."""
        import src.blog.signals  # noqa: F401
