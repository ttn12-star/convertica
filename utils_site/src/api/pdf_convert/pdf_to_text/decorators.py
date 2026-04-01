"""Swagger documentation decorators for PDF to Text API."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_text_docs():
    """Swagger docs for PDF to Text endpoint."""
    return swagger_auto_schema(
        operation_description=(
            "Extract plain text from a PDF file and return it as a .txt file."
        ),
        operation_summary="PDF to Text Converter",
        tags=["PDF Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "pdf_file",
                openapi.IN_FORM,
                description="PDF file to extract text from",
                type=openapi.TYPE_FILE,
                required=True,
            ),
            openapi.Parameter(
                "include_page_numbers",
                openapi.IN_FORM,
                description="Add page number dividers between pages",
                type=openapi.TYPE_BOOLEAN,
                default=False,
            ),
            openapi.Parameter(
                "preserve_layout",
                openapi.IN_FORM,
                description="Try to preserve text layout/columns",
                type=openapi.TYPE_BOOLEAN,
                default=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Plain text file",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request - invalid file or parameters",
            413: "File too large",
            500: "Conversion failed",
        },
    )
