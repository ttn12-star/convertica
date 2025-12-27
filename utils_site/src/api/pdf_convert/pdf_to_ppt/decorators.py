"""Swagger documentation decorators for PDF to PowerPoint API."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_ppt_docs():
    """Swagger documentation for PDF to PowerPoint conversion endpoint."""
    return swagger_auto_schema(
        operation_description="Convert PDF to PowerPoint (PPTX) format",
        operation_summary="PDF to PowerPoint Converter",
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
                "extract_images",
                openapi.IN_FORM,
                description="Extract and include images from PDF",
                type=openapi.TYPE_BOOLEAN,
                default=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="PowerPoint file",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request - invalid file or parameters",
            413: "File too large",
            500: "Conversion failed",
        },
    )
