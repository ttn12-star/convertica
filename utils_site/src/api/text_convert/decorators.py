"""Decorator for Text to PDF API documentation."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def text_to_pdf_docs():
    """Swagger documentation for Text to PDF API."""
    return swagger_auto_schema(
        operation_summary="Convert text to PDF",
        operation_description=(
            "Render pasted plain text into a PDF with global style options "
            "(font, size, color, alignment, page size, margins)."
        ),
        tags=["Text Conversion"],
        responses={
            200: openapi.Response(description="Conversion successful"),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Internal server error"),
        },
    )
