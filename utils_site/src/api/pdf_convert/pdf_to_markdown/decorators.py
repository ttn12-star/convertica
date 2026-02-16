"""Swagger documentation decorators for PDF to Markdown API."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_markdown_docs():
    """Swagger docs for PDF to Markdown endpoint."""
    return swagger_auto_schema(
        operation_description=(
            "Convert PDF to Markdown while preserving heading hierarchy and tables."
        ),
        operation_summary="PDF to Markdown Converter",
        tags=["PDF Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "pdf_file",
                openapi.IN_FORM,
                description="PDF file to convert",
                type=openapi.TYPE_FILE,
                required=True,
            ),
            openapi.Parameter(
                "detect_headings",
                openapi.IN_FORM,
                description="Detect heading hierarchy from font sizes",
                type=openapi.TYPE_BOOLEAN,
                default=True,
            ),
            openapi.Parameter(
                "preserve_tables",
                openapi.IN_FORM,
                description="Extract tables and render as Markdown tables",
                type=openapi.TYPE_BOOLEAN,
                default=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Markdown file",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request",
            403: "Premium subscription required",
            413: "File too large",
            500: "Conversion failed",
        },
    )
