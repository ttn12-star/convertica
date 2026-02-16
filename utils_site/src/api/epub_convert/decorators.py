"""Swagger documentation decorators for EPUB conversion APIs."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def epub_to_pdf_docs():
    """Swagger documentation for EPUB to PDF endpoint."""
    return swagger_auto_schema(
        operation_description="Convert EPUB eBook to PDF document",
        operation_summary="EPUB to PDF Converter",
        tags=["Premium Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "epub_file",
                openapi.IN_FORM,
                description="EPUB file to convert",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="PDF file",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request - invalid file",
            403: "Premium subscription required",
            413: "File too large",
            500: "Conversion failed",
        },
    )


def pdf_to_epub_docs():
    """Swagger documentation for PDF to EPUB endpoint."""
    return swagger_auto_schema(
        operation_description="Convert PDF document to EPUB eBook",
        operation_summary="PDF to EPUB Converter",
        tags=["Premium Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "pdf_file",
                openapi.IN_FORM,
                description="PDF file to convert",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="EPUB file",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request - invalid file",
            403: "Premium subscription required",
            413: "File too large",
            500: "Conversion failed",
        },
    )
