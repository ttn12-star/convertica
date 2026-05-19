"""URL router for /api/v1/* — the post-cutover API surface."""

from django.urls import path
from src.api.auth.views import web_token_view

# Import the view classes from their existing locations
from src.api.pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView

urlpatterns = [
    path("auth/web-token", web_token_view, name="v1_web_token"),
    # Tool endpoints — Phase 3 sweep
    path("jpg-to-pdf/", JPGToPDFAPIView.as_view(), name="v1_jpg_to_pdf"),
]
