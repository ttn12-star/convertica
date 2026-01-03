"""
User info API endpoint.
Provides user status and conversion limits.
"""

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class UserInfoAPIView(APIView):
    """API endpoint to get user information and conversion limits."""

    def get(self, request):
        """Return user premium status and conversion limits."""
        is_premium = False
        is_authenticated = False

        if request.user.is_authenticated:
            is_authenticated = True
            is_premium = getattr(request.user, "is_premium", False)

        return Response(
            {
                "is_authenticated": is_authenticated,
                "is_premium": is_premium,
                "limits": {
                    # HTML to PDF character limits
                    "html_to_pdf_max_chars": (
                        settings.HTML_TO_PDF_MAX_CHARS_PREMIUM
                        if is_premium
                        else settings.HTML_TO_PDF_MAX_CHARS_FREE
                    ),
                    "html_to_pdf_max_chars_free": settings.HTML_TO_PDF_MAX_CHARS_FREE,
                    "html_to_pdf_max_chars_premium": settings.HTML_TO_PDF_MAX_CHARS_PREMIUM,
                    # PDF page limits
                    "max_pdf_pages": (
                        settings.MAX_PDF_PAGES_PREMIUM
                        if is_premium
                        else settings.MAX_PDF_PAGES_FREE
                    ),
                    "max_pdf_pages_free": settings.MAX_PDF_PAGES_FREE,
                    "max_pdf_pages_premium": settings.MAX_PDF_PAGES_PREMIUM,
                    "max_pdf_pages_heavy": (
                        settings.MAX_PDF_PAGES_HEAVY_PREMIUM
                        if is_premium
                        else settings.MAX_PDF_PAGES_HEAVY_FREE
                    ),
                    "max_pdf_pages_heavy_free": settings.MAX_PDF_PAGES_HEAVY_FREE,
                    "max_pdf_pages_heavy_premium": settings.MAX_PDF_PAGES_HEAVY_PREMIUM,
                    # File size limits (in MB for easier frontend display)
                    "max_file_size_mb": (
                        settings.MAX_FILE_SIZE_PREMIUM / (1024 * 1024)
                        if is_premium
                        else settings.MAX_FILE_SIZE_FREE / (1024 * 1024)
                    ),
                    "max_file_size_free_mb": settings.MAX_FILE_SIZE_FREE
                    / (1024 * 1024),
                    "max_file_size_premium_mb": settings.MAX_FILE_SIZE_PREMIUM
                    / (1024 * 1024),
                    "max_file_size_heavy_mb": (
                        settings.MAX_FILE_SIZE_HEAVY_PREMIUM / (1024 * 1024)
                        if is_premium
                        else settings.MAX_FILE_SIZE_HEAVY_FREE / (1024 * 1024)
                    ),
                    "max_file_size_heavy_free_mb": settings.MAX_FILE_SIZE_HEAVY_FREE
                    / (1024 * 1024),
                    "max_file_size_heavy_premium_mb": settings.MAX_FILE_SIZE_HEAVY_PREMIUM
                    / (1024 * 1024),
                    # Batch processing limits
                    "max_batch_files": (
                        settings.MAX_BATCH_FILES_PREMIUM
                        if is_premium
                        else settings.MAX_BATCH_FILES_FREE
                    ),
                    "max_batch_files_free": settings.MAX_BATCH_FILES_FREE,
                    "max_batch_files_premium": settings.MAX_BATCH_FILES_PREMIUM,
                },
            },
            status=status.HTTP_200_OK,
        )
