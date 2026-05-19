"""URL router for /api/v1/* — the post-cutover API surface."""

from django.urls import path
from src.api.auth.views import web_token_view

urlpatterns = [
    path("auth/web-token", web_token_view, name="v1_web_token"),
    # Tool endpoints added in Task P3-2.
]
