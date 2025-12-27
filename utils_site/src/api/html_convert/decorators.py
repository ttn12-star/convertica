"""Decorators for HTML to PDF API documentation."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def html_to_pdf_docs():
    """Swagger documentation for HTML to PDF API."""
    return swagger_auto_schema(
        operation_summary="Convert HTML to PDF",
        operation_description="Convert HTML content to PDF using Playwright.",
        tags=["HTML Conversion"],
        responses={
            200: openapi.Response(description="Conversion successful"),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Internal server error"),
        },
    )


def url_to_pdf_docs():
    """Swagger documentation for URL to PDF API."""
    return swagger_auto_schema(
        operation_summary="Convert URL to PDF",
        operation_description="Convert web page to PDF using Playwright.",
        tags=["HTML Conversion"],
        responses={
            200: openapi.Response(description="Conversion successful"),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Internal server error"),
        },
    )
